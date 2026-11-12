#!/usr/bin/env python3
"""What should a forecast start from? A test on long daily history.

The Forecasts tab asks two things of every call: the chance the price is higher at the
end, and a range it should land in four times out of five. Before any news is read, both
need a starting point. This script tests candidates the only fair way: each is fitted on
the past and scored on the years after, never on data it has seen.

    python3 forecast_lab.py fetch --cache raw.json     # ten years of daily bars for about 110 symbols,
                                                       # and everything there is for five long-lived ones
    python3 forecast_lab.py test  --cache raw.json --out forecast_lab.json
    python3 forecast_lab.py freeze --cache raw.json    # constants for pipeline/refresh.py

Chance of a rise, candidates:
  now      what the pipeline used until now: the share of rises in the two years it holds
  coin     50%
  own      the asset's own share of rises over all the history before that day
  pool     the same share across every asset of its kind
  shrunk   own, pulled toward pool in proportion to how little history there is
  model    pool plus a small tilt from trend, momentum, recent moves and swing size

Range, candidates: the pipeline's band until now, and bands built from a forecast of the
swing (recent swings mixed with the long-run swing) times how far prices of that kind have
really landed, measured in swings.

It also measures one thing a forecast may fairly use: Tel Aviv closes hours before New York,
so the Tel Aviv price has not yet seen what the US did afterwards.

Needs numpy. Nothing here runs in the daily refresh; only the constants it prints do.
"""
import argparse
import datetime as dt
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pipeline"))
sys.path.insert(0, HERE)
import refresh as r  # noqa: E402

DAYS = (1, 7, 30, 90)
# kind -> symbols. "fund" is broad funds and indexes; "ref" is the Dow Jones list as it stood
# in 2010, which nobody picked for doing well since, so it shows what a "hot name" does next
# without the benefit of hindsight. It is pooled with the hot shares as kind "stock".
FUNDS = ["SPY", "^TA125.TA", "VFINX", "VGTSX", "QQQ", "IWM", "EFA", "EEM", "XLK", "XLF", "XLI", "XLV", "XLP", "XLE", "XLU", "XLB", "XLY"]
GOLD = ["IAU", "GC=F"]
FX = ["ILS=X", "EURUSD=X", "JPY=X", "GBPUSD=X"]
REF = ["MMM", "AXP", "T", "BAC", "BA", "CAT", "CVX", "CSCO", "KO", "XOM", "GE", "HPQ", "HD", "INTC", "IBM", "JNJ",
       "JPM", "MCD", "MRK", "MSFT", "PFE", "PG", "TRV", "VZ", "WMT", "DIS", "AA", "RTX", "MDLZ", "DD"]
MARKETS = ["SPY", "^TA125.TA", "BTC-USD", "IAU", "ILS=X"]     # the five on the Forecasts tab
LONG = ["SPY", "VFINX", "VGTSX", "GC=F", "BTC-USD"]           # fetched in full rather than for ten years
PPY = {"fund": 252, "stock": 252, "crypto": 365, "gold": 252, "fx": 260}
FEATURES = ("trend", "mom", "r1m", "r1w", "r1d", "swing", "dd")
# What the test chose as the starting point for each kind (see the results file): the long-run
# rate where it beat a coin flip on unseen years, and 50% where it did not. The model with
# trend, momentum and recent moves beat neither, anywhere, so nothing uses it.
PICK = {"fund": "shrunk", "gold": "shrunk", "stock": "pool", "crypto": "coin", "fx": "coin"}
SHRINK = 40.0          # own share of rises is mixed with this many independent stretches of the pool's
RIDGE = 100.0          # per bar of overlap: a 21-bar stretch shares 20 bars with its neighbour, so it is penalised 21 times over
FIRST_TEST_YEAR = 2008
Z80 = 1.2816


def universe():
    u = {}
    for s in FUNDS:
        u[s] = "fund"
    for s in GOLD:
        u[s] = "gold"
    for s in FX:
        u[s] = "fx"
    for s in list(r.HOT_STOCKS) + REF:
        u[s] = "stock"
    for s in r.HOT_COINS:
        u[s] = "crypto"
    return u


def bars_for(days, ppy):
    return max(1, int(round(days * ppy / 365.0)))


# ---- data ------------------------------------------------------------------------------

def fetch(cache, rng="10y"):
    """Daily closes in batches of ten symbols a request, with a long pause between requests.
    Symbols already in the cache are kept, so a longer history fetched some other way stays."""
    raw = json.load(open(cache)) if os.path.exists(cache) else {}
    from history_fetch import yahoo_daily_max
    for sym in LONG:                      # one request each for everything the source has; if it refuses, ten years will do
        if sym in raw:
            continue
        try:
            d, cl, _ = yahoo_daily_max(sym)
            raw[sym] = [d, [round(v, 6) for v in cl]]
            print("%-10s %s .. %s  %d bars" % (sym, d[0], d[-1], len(d)), flush=True)
            json.dump(raw, open(cache, "w"))
        except Exception as e:
            print("%-10s full history refused (%s)" % (sym, str(e)[:60]), flush=True)
        time.sleep(20)
    want = [s for s in universe() if s not in raw]
    for i in range(0, len(want), 10):
        got = r.yahoo_spark(want[i:i + 10], rng=rng)
        if not got:
            print("Nothing came back. The source may be asking us to slow down; run again later to carry on.")
            break
        for sym, (d, cl, _) in got.items():
            step = sorted((dt.date.fromisoformat(d[j + 1]) - dt.date.fromisoformat(d[j])).days for j in range(len(d) - 1))
            if step[len(step) // 2] > 3:
                print("%-10s skipped: bars are not daily" % sym, flush=True)
                continue
            raw[sym] = [d, [round(v, 6) for v in cl]]
            print("%-10s %s .. %s  %d bars" % (sym, d[0], d[-1], len(d)), flush=True)
        json.dump(raw, open(cache, "w"))
        time.sleep(20)
    print("%d of %d symbols" % (sum(1 for s in universe() if s in raw), len(universe())))


def clean(dates, px):
    """Drop wild one-day jumps that reverse the next day, which in this feed are bad prints."""
    p = np.array(px, dtype=float)
    keep = np.ones(len(p), dtype=bool)
    lr = np.diff(np.log(p))
    for i in range(1, len(p) - 1):
        if abs(lr[i - 1]) > 0.4 and abs(lr[i - 1] + lr[i]) < 0.1:
            keep[i] = False
    return [d for d, k in zip(dates, keep) if k], p[keep]


# ---- features and outcomes for one asset --------------------------------------------------

def roll_sum(x, k):
    c = np.concatenate([[0.0], np.cumsum(np.nan_to_num(x))])
    out = np.full(len(x), np.nan)
    out[k - 1:] = c[k:] - c[:-k]
    return out


def roll_sd(ret, k):
    """Standard deviation of the last k daily log returns, at each bar."""
    m = roll_sum(ret, k) / k
    v = roll_sum(ret * ret, k) / k - m * m
    return np.sqrt(np.maximum(v, 1e-12) * k / (k - 1.0))


def roll_max(x, k):
    w = np.lib.stride_tricks.sliding_window_view(x, k)
    out = np.full(len(x), np.nan)
    out[k - 1:] = w.max(axis=1)
    return out


class Asset:
    def __init__(self, sym, kind, dates, px):
        self.sym, self.kind, self.ppy = sym, kind, PPY[kind]
        self.dates, self.p = clean(dates, px)
        self.n = len(self.p)
        self.day = np.array([int(d.replace("-", "")) for d in self.dates])
        lp = np.log(self.p)
        self.lp = lp
        ret = np.concatenate([[0.0], np.diff(lp)])
        ret[0] = np.nan
        self.ret = ret
        ppy = self.ppy
        k1w, k1m, k12 = bars_for(7, ppy), bars_for(30, ppy), ppy
        self.v5, self.v20, self.v60, self.v250 = (roll_sd(ret, k) for k in (5, 20, 60, 250))
        sma200 = roll_sum(self.p, 200) / 200.0

        def back(k):
            out = np.full(self.n, np.nan)
            out[k:] = lp[k:] - lp[:-k]
            return out
        r12 = back(k12)
        f = {
            "trend": (lp - np.log(sma200)) / (self.v250 * math.sqrt(100)),
            "mom": (r12 - back(k1m)) / (self.v250 * math.sqrt(k12 - k1m)),
            "r1m": back(k1m) / (self.v60 * math.sqrt(k1m)),
            "r1w": back(k1w) / (self.v20 * math.sqrt(k1w)),
            "r1d": ret / self.v20,
            "swing": np.log(self.v20 / self.v250),
            "dd": (lp - roll_max(lp, k12)) / (self.v250 * math.sqrt(k12)),
        }
        self.X = np.clip(np.column_stack([f[k] for k in FEATURES]), -4, 4)
        self.r12 = r12
        self.ok = ~np.isnan(self.X).any(axis=1) & ~np.isnan(self.v250)

    def outcome(self, days):
        """(k, up, move): bars ahead, 1.0 where the price was higher k bars on, the log move."""
        k = bars_for(days, self.ppy)
        up, mv = np.full(self.n, np.nan), np.full(self.n, np.nan)
        mv[:-k] = self.lp[k:] - self.lp[:-k]
        up[:-k] = (self.p[k:] > self.p[:-k]).astype(float)
        return k, up, mv

    def now_rate(self, days):
        """The pipeline's old base rate: share of rises among the k-bar stretches inside the two
        years it holds (inside the last year for one day)."""
        k, up, _ = self.outcome(days)
        W = self.ppy if days == 1 else 2 * self.ppy
        c = np.concatenate([[0.0], np.cumsum(np.nan_to_num(up))])
        out = np.full(self.n, np.nan)
        t = np.arange(W, self.n)
        out[t] = (c[t - k + 1] - c[t - W]) / float(W - k + 1)
        return out

    def own_rate(self, days):
        """(ups, stretches) finished by each bar, over all history before it."""
        k, up, _ = self.outcome(days)
        c = np.concatenate([[0.0], np.cumsum(np.nan_to_num(up))])
        t = np.arange(self.n)
        done = np.maximum(t - k + 1, 0)
        return c[done], done.astype(float)


def load(cache):
    raw, u = json.load(open(cache)), universe()
    out = {}
    for sym, kind in u.items():
        if sym in raw and len(raw[sym][0]) > 600:
            out[sym] = Asset(sym, kind, raw[sym][0], raw[sym][1])
    return out


def hot_flags(assets, names, n=5):
    """For each asset in `names`, a boolean array: was it among the n with the best twelve
    months on that day? This is how the pipeline picks its hot names."""
    by_day = {}
    for s in names:
        a = assets.get(s)
        if a is None:
            continue
        for i in np.nonzero(~np.isnan(a.r12))[0]:
            by_day.setdefault(a.day[i], []).append((a.r12[i], s, i))
    flags = {s: np.zeros(assets[s].n, dtype=bool) for s in names if s in assets}
    for day, rows in by_day.items():
        if len(rows) < 2 * n:
            continue
        for _, s, i in sorted(rows, reverse=True)[:n]:
            flags[s][i] = True
    return flags


# ---- one table per (kind, horizon) -----------------------------------------------------------

def table(assets, kind, days):
    """Every usable (asset, day) of a kind: features, outcome and the simple candidates."""
    cols = {k: [] for k in ("sym", "day", "end", "up", "mv", "now", "ownU", "ownN", "k", "v5", "v20", "v60", "v250", "i")}
    X = []
    syms = [s for s, a in assets.items() if a.kind == kind]
    for si, s in enumerate(syms):
        a = assets[s]
        k, up, mv = a.outcome(days)
        ownU, ownN = a.own_rate(days)
        m = a.ok & ~np.isnan(up)
        idx = np.nonzero(m)[0]
        cols["sym"].append(np.full(len(idx), si))
        cols["day"].append(a.day[idx])
        cols["end"].append(a.day[idx + k])
        cols["up"].append(up[idx])
        cols["mv"].append(mv[idx])
        cols["now"].append(a.now_rate(days)[idx])
        cols["ownU"].append(ownU[idx])
        cols["ownN"].append(ownN[idx])
        cols["k"].append(np.full(len(idx), k))
        for v in ("v5", "v20", "v60", "v250"):
            cols[v].append(getattr(a, v)[idx])
        cols["i"].append(idx)
        X.append(a.X[idx])
    T = {k: np.concatenate(v) for k, v in cols.items()}
    T["X"], T["syms"] = np.vstack(X), syms
    # pool: share of rises over every stretch of this kind that had finished by the day
    order = np.argsort(T["end"], kind="stable")
    ends, cu = T["end"][order], np.cumsum(T["up"][order])
    pos = np.searchsorted(ends, T["day"], side="right")       # stretches ended on or before the day
    T["pool"] = np.where(pos > 0, cu[np.maximum(pos - 1, 0)] / np.maximum(pos, 1), 0.5)
    kk = T["k"].astype(float)
    eff = T["ownN"] / kk                                      # independent stretches of its own
    own = np.where(T["ownN"] > 0, T["ownU"] / np.maximum(T["ownN"], 1), T["pool"])
    T["own"] = own
    T["shrunk"] = (eff * own + SHRINK * T["pool"]) / (eff + SHRINK)
    T["now"] = np.where(np.isnan(T["now"]), T["pool"], T["now"])
    return T


def logit(p):
    p = np.clip(p, 0.02, 0.98)
    return np.log(p / (1 - p))


def fit_logistic(X, y, offset, ridge=50.0, steps=12):
    """Logistic regression with a fixed offset (the shrunk base rate, as log-odds), so the
    features only explain what the base rate does not. A firm ridge keeps the tilts small."""
    Xb = np.column_stack([np.ones(len(X)), X])
    w = np.zeros(Xb.shape[1])
    pen = np.full(Xb.shape[1], ridge)
    pen[0] = 1e-6
    for _ in range(steps):
        z = np.clip(offset + Xb @ w, -30, 30)
        p = 1 / (1 + np.exp(-z))
        g = Xb.T @ (p - y) + pen * w
        H = (Xb * (p * (1 - p))[:, None]).T @ Xb + np.diag(pen)
        step = np.linalg.solve(H, g)
        w -= step
        if np.abs(step).max() < 1e-7:
            break
    return w


def predict(w, X, offset):
    return 1 / (1 + np.exp(-np.clip(offset + w[0] + X @ w[1:], -30, 30)))


VOL_PARTS = ("v5", "v20", "v60", "v250")


def fit_vol(T, m):
    """Weights on recent and long-run variance that best forecast the variance actually seen
    over the stretch (non-negative, summing to whatever fits)."""
    A = np.column_stack([T[v][m] ** 2 for v in VOL_PARTS])
    b = (T["mv"][m] ** 2) / T["k"][m]
    scale = np.median(A[:, 3])
    A, b = A / scale, np.clip(b / scale, 0, 25)            # tame the few huge days
    w = np.full(4, 0.25)
    for _ in range(400):                                    # projected gradient, tiny problem
        g = A.T @ (A @ w - b) / len(b)
        w = np.maximum(w - 0.02 * g, 0)
    return w


def vol_forecast(T, w, m=slice(None)):
    return np.sqrt(np.maximum(sum(w[j] * T[v][m] ** 2 for j, v in enumerate(VOL_PARTS)), 1e-12))


def walk_forward(T, days):
    """Adds T['model'] (chance of a rise) and T['lo'], T['hi'] (80% range as log moves), each
    fitted only on stretches that had finished before the test year began."""
    n = len(T["day"])
    T["model"] = np.full(n, np.nan)
    T["lo"], T["hi"] = np.full(n, np.nan), np.full(n, np.nan)
    T["sig"] = np.full(n, np.nan)
    years = T["day"] // 10000
    off = logit(T["shrunk"])
    for year in range(FIRST_TEST_YEAR, int(years.max()) + 1):
        train = T["end"] < year * 10000 + 101
        test = years == year
        if train.sum() < 3000 or not test.any():
            continue
        w = fit_logistic(T["X"][train], T["up"][train], off[train], ridge=RIDGE * T["k"][0])
        T["model"][test] = predict(w, T["X"][test], off[test])
        vw = fit_vol(T, train)
        sd = vol_forecast(T, vw, train) * np.sqrt(T["k"][train])
        z = T["mv"][train] / sd
        q10, q90 = np.quantile(z, 0.10), np.quantile(z, 0.90)
        sdt = vol_forecast(T, vw, test) * np.sqrt(T["k"][test])
        T["sig"][test] = sdt
        T["lo"][test], T["hi"][test] = q10 * sdt, q90 * sdt
    return T


def old_band(a, days, idx):
    """The pipeline's band until now, for the bars in idx: the middle 80% of the asset's k-bar
    moves in the two years it holds, measured from the median, stretched by recent swing."""
    k = bars_for(days, a.ppy)
    W = 2 * a.ppy
    lo, hi = np.full(len(idx), np.nan), np.full(len(idx), np.nan)
    for j, t in enumerate(idx):
        if t < W:
            continue
        w = a.lp[t - W:t + 1]
        mv = np.sort(w[k:] - w[:-k])
        if len(mv) < 120:
            continue
        mid = mv[len(mv) // 2]
        b0, b1 = mv[int(0.10 * (len(mv) - 1))] - mid, mv[int(round(0.90 * (len(mv) - 1)))] - mid
        vol_all = np.std(np.diff(w), ddof=1)
        scale = min(1.8, max(0.6, 0.5 * (a.v20[t] + a.v60[t]) / vol_all))
        lo[j], hi[j] = b0 * scale, b1 * scale
    return lo, hi


# ---- Tel Aviv closes before New York -------------------------------------------------------------

LAG_CLIP = 3.0          # a US move is counted up to 3% either way
LAG_RIDGE = 5.0


def lag_rows(assets):
    """For each Tel Aviv bar: the US move that came after its close and before its next bar
    (which the Tel Aviv price has not seen), and what Tel Aviv then did over 1 and 5 bars."""
    import bisect
    ta, us = assets.get("^TA125.TA"), assets.get("SPY")
    if ta is None or us is None:
        return None
    before = lambda d: bisect.bisect_left(us.dates, d) - 1      # last US session strictly before a date
    year, gap, up1, up5 = [], [], [], []
    for i in range(1, ta.n - 5):
        a, b = before(ta.dates[i]), before(ta.dates[i + 1])
        if a < 0:
            continue
        year.append(int(ta.dates[i][:4]))
        gap.append(100 * (us.lp[b] - us.lp[a]))
        up1.append(float(ta.p[i + 1] > ta.p[i]))
        up5.append(float(ta.p[i + 5] > ta.p[i]))
    return np.array(year), np.clip(np.array(gap), -LAG_CLIP, LAG_CLIP), {1: np.array(up1), 7: np.array(up5)}


def lag_fit(x, y):
    """Log-odds = a + c * (US move in %). Returns (a, c)."""
    w = fit_logistic(x[:, None], y, np.zeros(len(y)), ridge=LAG_RIDGE, steps=30)
    return float(w[0]), float(w[1])


def tel_aviv_lag(assets):
    rows = lag_rows(assets)
    if rows is None:
        return None
    year, gap, ups = rows
    out = {"bars": int(len(gap)), "from": int(year.min()), "to": int(year.max()), "days": {}}
    for days, y in ups.items():
        eb, em = [], []
        for yr in range(int(year.min()) + 3, int(year.max()) + 1):
            tr, te = year < yr, year == yr
            if not te.any():
                continue
            a, c = lag_fit(gap[tr], y[tr])
            eb.extend((y[tr].mean() - y[te]) ** 2)
            em.extend((1 / (1 + np.exp(-(a + c * gap[te]))) - y[te]) ** 2)
        a, c = lag_fit(gap, y)
        groups = []
        for lo, hi, label in ((-99, -1, "US fell 1% or more"), (-1, -0.3, "US fell 0.3% to 1%"), (-0.3, 0.3, "US flat"),
                              (0.3, 1, "US rose 0.3% to 1%"), (1, 99, "US rose 1% or more")):
            m = (gap > lo) & (gap <= hi)
            groups.append({"label": label, "n": int(m.sum()), "rose": round(float(y[m].mean()), 3)})
        out["days"][str(days)] = {"plain": round(float(np.mean(eb)), 5), "withUS": round(float(np.mean(em)), 5),
                                  "skill": round(float(1 - np.mean(em) / np.mean(eb)), 4), "tested": len(eb),
                                  "coef": round(c, 3), "groups": groups}
    return out


# ---- scoring -----------------------------------------------------------------------------------

def brier(p, y):
    return (p - y) ** 2


def blocks_of(day, days):
    """Calendar months (quarters for the three-month calls): prices of one month move together."""
    ym = day // 100
    return ym if days < 90 else (ym // 100) * 10 + ((ym % 100) - 1) // 3


def skill_row(T, m, days, rng, draws=600):
    """Brier of each candidate on rows m, and skill against `now` with a 90% interval from
    resampling whole months."""
    y = T["up"][m]
    out = {"n": int(m.sum()), "rose": round(float(y.mean()), 4)}
    b = blocks_of(T["day"][m], days)
    ub, inv = np.unique(b, return_inverse=True)
    base = brier(T["now"][m], y)
    sums_base = np.bincount(inv, base)
    for name in ("now", "coin", "own", "pool", "shrunk", "model"):
        p = np.full(m.sum(), 0.5) if name == "coin" else T[name][m]
        e = brier(p, y)
        out[name] = round(float(e.mean()), 5)
        if name != "now":
            sums = np.bincount(inv, e)
            pick = rng.integers(0, len(ub), size=(draws, len(ub)))
            sk = 1 - sums[pick].sum(axis=1) / sums_base[pick].sum(axis=1)
            out[name + "Skill"] = [round(float(1 - e.mean() / base.mean()), 4)] + [round(float(v), 4) for v in np.quantile(sk, [0.05, 0.95])]
    out["blocks"] = int(len(ub))
    tilt = T["model"][m] - T["shrunk"][m]
    out["tilt"] = [round(float(v), 4) for v in np.quantile(tilt, [0.05, 0.95])]
    return out


def range_row(lo, hi, mv, unit):
    """Coverage, and the interval score (width plus ten times any miss), both in units of the
    asset's own long-run swing so that calm and wild assets count alike."""
    ok = ~np.isnan(lo) & ~np.isnan(hi)
    lo, hi, mv, unit = lo[ok], hi[ok], mv[ok], unit[ok]
    miss = np.maximum(lo - mv, 0) + np.maximum(mv - hi, 0)
    return {"n": int(ok.sum()), "inside": round(float(((mv >= lo) & (mv <= hi)).mean()), 4),
            "width": round(float(((hi - lo) / unit).mean()), 4),
            "score": round(float((((hi - lo) + 10 * miss) / unit).mean()), 4)}


def test(cache, out_path):
    assets = load(cache)
    rng = np.random.default_rng(20261112)
    flags = {"hot": hot_flags(assets, list(r.HOT_STOCKS)), "ref": hot_flags(assets, REF),
             "coin": hot_flags(assets, list(r.HOT_COINS))}
    res = {"generatedAt": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "firstTestYear": FIRST_TEST_YEAR, "symbols": len(assets), "chance": [], "range": []}
    for kind in ("fund", "stock", "crypto", "gold", "fx"):
        if not any(x.kind == kind for x in assets.values()):
            continue
        for days in DAYS:
            T = walk_forward(table(assets, kind, days), days)
            tested = ~np.isnan(T["model"])
            sym = np.array(T["syms"])[T["sym"]]
            groups = [("all " + kind, tested)]
            for s in MARKETS:
                if s in T["syms"]:
                    groups.append((s, tested & (sym == s)))
            if kind in ("stock", "crypto"):
                for tag, names in (("hot shares", "hot"), ("2010 Dow list, best five", "ref")) if kind == "stock" else (("hot coins", "coin"),):
                    f = np.zeros(len(sym), dtype=bool)
                    for s, fl in flags[names].items():
                        rows = sym == s
                        f[rows] = fl[T["i"][rows]]
                    groups.append((tag, tested & f))
            for label, m in groups:
                if m.sum() < 200:
                    continue
                row = {"group": label, "kind": kind, "days": days}
                row.update(skill_row(T, m, days, rng))
                row["pick"] = PICK[kind]
                res["chance"].append(row)
                # ranges: only where the page shows them (markets at 7/30/90, hot names at one day)
                market = label in MARKETS and days != 1
                hot = label.startswith("hot") and days == 1
                if not (market or hot):
                    continue
                unit = T["v250"][m] * np.sqrt(T["k"][m])
                lo0, hi0 = np.full(m.sum(), np.nan), np.full(m.sum(), np.nan)
                where = np.nonzero(m)[0]
                step = 1 if market else 3                 # the old band is slow to rebuild; sample the hot rows
                for s in set(sym[where]):
                    rows = where[sym[where] == s][::step]
                    l, h_ = old_band(assets[s], days, T["i"][rows])
                    at = np.searchsorted(where, rows)
                    lo0[at], hi0[at] = l, h_
                rr = {"group": label, "kind": kind, "days": days}
                rr["now"] = range_row(lo0, hi0, T["mv"][m], unit)
                rr["new"] = range_row(np.where(np.isnan(lo0), np.nan, T["lo"][m]), T["hi"][m], T["mv"][m], unit)
                bell = Z80 * T["v20"][m] * np.sqrt(T["k"][m])
                rr["bell20"] = range_row(np.where(np.isnan(lo0), np.nan, -bell), bell, T["mv"][m], unit)
                res["range"].append(rr)
            print("done %s %dd" % (kind, days), flush=True)
    res["telAviv"] = tel_aviv_lag(assets)
    json.dump(res, open(out_path, "w"), indent=1)
    show(res)


def show(res):
    print("\nChance of a rise: Brier score, lower is better. Skill is against the old base rate, with a 90% interval.")
    print("%-26s %3s %7s %6s | %7s %7s %7s %7s %7s %7s | %-24s %-24s" % (
        "group", "d", "n", "rose", "now", "coin", "own", "pool", "shrunk", "model", "shrunk skill", "model skill"))
    for x in res["chance"]:
        print("%-26s %3d %7d %5.1f%% | %7.4f %7.4f %7.4f %7.4f %7.4f %7.4f | %+6.2f%% (%+.2f to %+.2f)  %+6.2f%% (%+.2f to %+.2f)" % (
            x["group"][:26], x["days"], x["n"], 100 * x["rose"], x["now"], x["coin"], x["own"], x["pool"], x["shrunk"], x["model"],
            *[100 * v for v in x["shrunkSkill"]], *[100 * v for v in x["modelSkill"]])
            + "  tilt %+.1f to %+.1f pts" % (100 * x["tilt"][0], 100 * x["tilt"][1]))
    print("\nRanges meant to hold 80% of outcomes: share inside, width and score in long-run swings (lower score is better).")
    for x in res["range"]:
        print("%-12s %3dd  n=%6d | now %4.1f%% w %.2f s %.3f | new %4.1f%% w %.2f s %.3f | bell(20d) %4.1f%% w %.2f s %.3f" % (
            x["group"][:12], x["days"], x["now"]["n"], 100 * x["now"]["inside"], x["now"]["width"], x["now"]["score"],
            100 * x["new"]["inside"], x["new"]["width"], x["new"]["score"],
            100 * x["bell20"]["inside"], x["bell20"]["width"], x["bell20"]["score"]))


    ta = res.get("telAviv")
    if ta:
        print("\nTel Aviv 125 after a US move it has not seen (%d bars, %d-%d):" % (ta["bars"], ta["from"], ta["to"]))
        for d, x in ta["days"].items():
            print("  %s-day call: Brier %.4f plain, %.4f using the US move, skill %+.2f%% on %d bars | log-odds per 1%% US move %.3f | %s" % (
                d, x["plain"], x["withUS"], 100 * x["skill"], x["tested"], x["coef"],
                "; ".join("%s: rose %.0f%% (n=%d)" % (g["label"], 100 * g["rose"], g["n"]) for g in x["groups"])))


def freeze(cache):
    """Fit once on everything and print the constants the pipeline carries: a starting chance
    for each market and kind, and for each kind and horizon the mix of recent and long-run
    swing plus how far prices landed, in swings, at the 10th and 90th percentile."""
    assets = load(cache)
    start, rng = {}, {}
    for kind in ("fund", "stock", "crypto", "gold", "fx"):
        if not any(x.kind == kind for x in assets.values()):
            continue
        for days in DAYS:
            T = table(assets, kind, days)
            vw = fit_vol(T, np.ones(len(T["day"]), dtype=bool))
            z = T["mv"] / (vol_forecast(T, vw) * np.sqrt(T["k"]))
            rng["%s:%d" % (kind, days)] = {"vol": [round(float(v), 3) for v in vw],
                                           "z": [round(float(np.quantile(z, 0.10)), 3), round(float(np.quantile(z, 0.90)), 3)]}
            pool = float(T["up"].mean())
            start.setdefault(kind, {})[str(days)] = 0.5 if PICK[kind] == "coin" else round(pool, 3)
            if PICK[kind] != "shrunk":
                continue
            for s in MARKETS:
                # the longest history of the same thing: gold futures stand in for the gold fund
                same = [assets[x] for x in (GOLD if s in GOLD else [s]) if x in assets and assets[x].kind == kind]
                if not same:
                    continue
                a = max(same, key=lambda x: x.n)
                k, up, _ = a.outcome(days)
                done = up[~np.isnan(up)]
                eff = len(done) / float(k)
                start.setdefault(s, {})[str(days)] = round(float((eff * done.mean() + SHRINK * pool) / (eff + SHRINK)), 3)
    ta = tel_aviv_lag(assets)
    lag = {d: x["coef"] for d, x in ta["days"].items()} if ta else {}
    print(json.dumps({"start": start, "range": rng, "telAvivLag": lag}, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=["fetch", "test", "freeze", "show"])
    ap.add_argument("--cache", default="forecast_raw.json")
    ap.add_argument("--out", default=os.path.join(HERE, "forecast_lab.json"))
    a = ap.parse_args()
    if a.mode == "fetch":
        fetch(a.cache)
    elif a.mode == "test":
        test(a.cache, a.out)
    elif a.mode == "freeze":
        freeze(a.cache)
    else:
        show(json.load(open(a.out)))


if __name__ == "__main__":
    main()
