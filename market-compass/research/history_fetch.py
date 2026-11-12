#!/usr/bin/env python3
"""Replay the pipeline's readings on history, for testing the model.

For each month-end it rebuilds the readings the pipeline would have produced with
only the data available that day, using the same functions and weights as
refresh.py, and records what each part of the plan earned in the following month.

    python3 history_fetch.py --out history.json
    node backtest.js history.json

What is the same as the live pipeline: trend (200-day average, 12-month return over
T-bills, 3-month return), credit, volatility, the rate-shock test, valuation and its
cap, yield after inflation, inflation level and direction, the dollar, and gold's
real-rate reading.

What differs, because the live inputs have no long history:
  * Long-lived index mutual funds stand in for the ETFs (VFINX for US stocks, VGTSX
    for international, VBMFX for bonds, VWEHX against VFITX for credit).
  * Market breadth (a twentieth of the risk reading), crypto liquidity and crowd mood
    (a twentieth each of the crypto reading) are left out; their weight is shared
    among the parts that remain, exactly as the live pipeline does when a feed fails.
  * The news brief does not exist in the past, so it plays no part.
"""
import argparse
import bisect
import datetime as dt
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pipeline"))
import refresh as r  # noqa: E402

FUNDS = {"us": "VFINX", "intl": "VGTSX", "bonds": "VBMFX", "gold": "GC=F", "crypto": "BTC-USD"}
EXTRA = {"hy": "VWEHX", "ust": "VFITX", "y3m": "^IRX", "y5y": "^FVX", "y10y": "^TNX", "dxy": "DX-Y.NYB"}
PPY = {"crypto": 365}
START = int(dt.datetime(1990, 1, 1, tzinfo=dt.timezone.utc).timestamp())


def yahoo_daily_max(symbol):
    """Every daily bar Yahoo has: (dates, close, adjusted close or close)."""
    q = urllib.parse.quote(symbol)
    last = None
    for h in ("query2.finance.yahoo.com", "query1.finance.yahoo.com"):
        try:
            # explicit dates: with range=max Yahoo quietly answers in monthly or quarterly bars
            d = r.get_json("https://%s/v8/finance/chart/%s?period1=%d&period2=%d&interval=1d&events=div" % (
                h, q, START, int(r.NOW().timestamp())), tries=4, timeout=120)
            res = d["chart"]["result"][0]
            ts = res["timestamp"]
            cl = res["indicators"]["quote"][0]["close"]
            adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose") or cl
            rows = {}
            for t, c, a in zip(ts, cl, adj):
                if c and a and c > 0 and a > 0:
                    rows[dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d")] = (float(c), float(a))
            days = sorted(rows)
            return days, [rows[k][0] for k in days], [rows[k][1] for k in days]
        except Exception as e:
            last = e
    raise RuntimeError("history %s: %s" % (symbol, last))


class Series:
    def __init__(self, dates, px, tr):
        self.dates, self.px, self.tr = dates, px, tr

    def upto(self, day):
        """Index one past the last bar on or before `day`."""
        return bisect.bisect_right(self.dates, day)

    def last(self, day):
        i = self.upto(day)
        return self.px[i - 1] if i else None


def month_ends(dates, first, last):
    """The last trading day of each month between two YYYY-MM strings, inclusive."""
    out, prev = [], None
    for d in dates:
        if prev and prev[:7] != d[:7] and first <= prev[:7] <= last:
            out.append(prev)
        prev = d
    return out


def scores_on(day, S, cape_hist, cpi_rows, cash12m):
    """The six sleeve readings as refresh.build() would have made them on `day`."""
    def info(key, need):
        s = S.get(key)
        if not s:
            return None
        i = s.upto(day)
        if i < need:
            return None
        ppy = PPY.get(key, 252)
        lo = max(0, i - (ppy + 180))
        return r.analyze(s.dates[lo:i], s.px[lo:i], s.tr[lo:i], ppy)

    def val(key, back=0):
        s = S.get(key)
        i = s.upto(day) if s else 0
        return s.px[i - 1 - back] if i > back else None

    a = {k: info(k, 253 if k != "crypto" else 366) for k in FUNDS}

    def trend(key):
        if not a[key]:
            return None
        parts = r.crypto_trend_parts(a[key], cash12m) if key == "crypto" else r.trend_parts(a[key], cash12m)
        return r.combine(parts)

    # macro, as known that day. CPI for a month is published in the middle of the next one.
    known = [row for row in cpi_rows if row[0][:7] < day[:7]]
    cpi = known[-1][1] if known else None
    cpi3 = known[-4][1] if len(known) > 3 else None
    y5, y10, y10_3m = val("y5y"), val("y10y"), val("y10y", 63)
    y10chg = None if y10 is None or y10_3m is None else y10 - y10_3m
    dxy = info("dxy", 253)
    dollar = None if not dxy or dxy.get("vs200") is None else -r.soft(dxy["vs200"], 0.03)

    # risk conditions
    credit = None
    hy, ust = S.get("hy"), S.get("ust")
    if hy and ust:
        ih, iu = hy.upto(day), ust.upto(day)
        mh = dict(zip(hy.dates[max(0, ih - 320):ih], hy.tr[max(0, ih - 320):ih]))
        mu = dict(zip(ust.dates[max(0, iu - 320):iu], ust.tr[max(0, iu - 320):iu]))
        ratio = [mh[d] / mu[d] for d in sorted(set(mh) & set(mu))]
        if len(ratio) > 200:
            credit = r.clamp(0.6 * r.soft(r.pct(ratio[-1], r.sma(ratio, 200)), 0.03) + 0.4 * r.soft(r.ret(ratio, 63), 0.03))
    vol = r.volatility_reading(a["us"]["vol20"], 0.16) if a["us"] else None
    rates = r.rate_shock_reading(y10chg)
    regime = r.combine([{"score": credit, "weight": 0.50}, {"score": vol, "weight": 0.30}, {"score": rates, "weight": 0.15}])

    def mix(*pairs):
        return r.combine([{"score": s, "weight": w} for s, w in pairs])

    hist = [row for row in cape_hist if row[0][:7] <= day[:7]]
    v_score, v_pct = r.valuation_reading(hist, hist[-1][1], 40) if hist else (None, None)
    us = mix((trend("us"), 0.70), (regime, 0.20), (v_score, 0.10))
    if us is not None and v_pct is not None and v_pct >= 90 and us > 0.5:
        us = 0.5

    carry = None if y5 is None or cpi is None else r.clamp((y5 - cpi - 0.5) / 1.5)
    infl = None
    if cpi is not None and cpi3 is not None:
        infl = r.clamp(0.5 * r.clamp(-(cpi - cpi3) / 0.5) - 0.5 * r.clamp((cpi - 2.5) / 1.5))
    real = None if y10chg is None else -r.soft(y10chg - ((cpi - cpi3) if cpi is not None and cpi3 is not None else 0.0), 0.6)

    out = {
        "us": us,
        "intl": mix((trend("intl"), 0.65), (regime, 0.20), (dollar, 0.15)) if a["intl"] else None,
        "bonds": mix((trend("bonds"), 0.45), (carry, 0.30), (infl, 0.25)) if a["bonds"] else None,
        "gold": mix((trend("gold"), 0.75), (real, 0.10), (dollar, 0.15)) if a["gold"] else None,
        "crypto": mix((trend("crypto"), 0.65), (regime, 0.25)) if a["crypto"] else None,
    }
    parts = {"regime": regime, "credit": credit, "vol": vol, "rates": rates, "capePct": v_pct, "cpi": cpi,
             "trendUs": trend("us")}
    return ({k: (None if v is None else round(v, 4)) for k, v in out.items()},
            {k: (None if v is None else round(v, 4)) for k, v in parts.items()})


def load_raw(cache=None):
    """Download every series, or reuse a cache file from an earlier run."""
    if cache and os.path.exists(cache):
        with open(cache) as f:
            return json.load(f)
    raw = {"series": {}}
    for key, sym in list(FUNDS.items()) + list(EXTRA.items()):
        d, c, adj = yahoo_daily_max(sym)
        raw["series"][key] = [d, c, adj]
        print("  %-6s %-9s %s to %s  %d days" % (key, sym, d[0], d[-1], len(d)), file=sys.stderr)
    raw["cape"] = r.multpl_history("shiller-pe")
    raw["cpi"] = r.multpl_history("inflation")
    if cache:
        with open(cache, "w") as f:
            json.dump(raw, f)
    return raw


def build(first="1997-05", lag=0, cache=None):
    """lag: how many trading days before the month-end the readings are taken.
    0 reads and trades on the same close; 1 is what someone acting the next morning gets."""
    raw = load_raw(cache)
    S = {}
    for key, (d, c, adj) in raw["series"].items():
        S[key] = Series(d, c, adj if key in FUNDS or key in ("hy", "ust") else c)
    cape_hist = [tuple(x) for x in raw["cape"]]
    cpi_rows = [tuple(x) for x in raw["cpi"]]

    this_month = r.NOW().strftime("%Y-%m")
    ends = month_ends(S["us"].dates, "1996-01", "9999-12")
    ends = [d for d in ends if d[:7] < this_month]          # finished months only
    # one month of cash is last month's T-bill yield, a twelfth of it
    cash_ret = {}
    for i in range(1, len(ends)):
        y = S["y3m"].last(ends[i - 1])
        cash_ret[ends[i][:7]] = None if y is None else y / 1200.0

    rows = []
    for i, day in enumerate(ends[:-1]):
        if day[:7] < first:
            continue
        nxt = ends[i + 1]
        back = [cash_ret.get(e[:7]) for e in ends[max(0, i - 11):i + 1]]
        cash12 = None
        if len(back) == 12 and all(x is not None for x in back):
            cash12 = 1.0
            for x in back:
                cash12 *= 1 + x
            cash12 -= 1
        seen = S["us"].dates[max(0, S["us"].upto(day) - 1 - lag)]
        scores, parts = scores_on(seen, S, cape_hist, cpi_rows, cash12)
        rets = {}
        for k in FUNDS:
            s = S[k]
            i0, i1 = s.upto(day), s.upto(nxt)
            # a fund counts for the month only if it traded near both month-ends
            ok = i0 and i1 > i0 and s.dates[i0 - 1][:7] == day[:7] and s.dates[i1 - 1][:7] == nxt[:7]
            rets[k] = round(s.tr[i1 - 1] / s.tr[i0 - 1] - 1, 6) if ok else None
        rets["cash"] = None if cash_ret.get(nxt[:7]) is None else round(cash_ret[nxt[:7]], 6)
        rows.append({"asOf": day, "next": nxt[:7], "scores": scores, "parts": parts, "ret": rets})
    return {"generatedAt": r.NOW().strftime("%Y-%m-%dT%H:%M:%SZ"), "funds": dict(FUNDS, cash="^IRX"), "lag": lag, "rows": rows}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Replay Market Compass readings on history")
    ap.add_argument("--out", default="history.json")
    ap.add_argument("--first", default="1997-05", help="first month-end to score, YYYY-MM")
    ap.add_argument("--lag", type=int, default=1, help="trading days between reading the signals and trading on them")
    ap.add_argument("--cache", help="file to keep the downloaded series in, to re-run without downloading")
    args = ap.parse_args()
    data = build(args.first, args.lag, args.cache)
    with open(args.out, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    rows = data["rows"]
    print("%d months, %s to %s -> %s" % (len(rows), rows[0]["asOf"], rows[-1]["next"], args.out))
