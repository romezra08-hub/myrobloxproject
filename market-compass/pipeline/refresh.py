#!/usr/bin/env python3
"""Market Compass data refresh.

Pulls live prices, yields, valuation, crypto and headline data from free public
feeds, computes every indicator the app's model uses, and writes:

    <out>/snapshot.json    the document the app page renders from
    <out>/headlines.json   a longer headline list for the news-brief step

Standard library only. Run:  python3 refresh.py --out ./out

Design rules
  * Every source is optional. A failed feed is recorded under "sources" and the
    indicators that depend on it are left out; nothing is ever invented.
  * Requests identify themselves honestly and back off when a feed says slow down.
  * All scoring lives here so the page and the tests share one definition.
"""
import argparse
import datetime as dt
import html
import json
import math
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = "market-compass/1.0 (personal research script)"
NOW = lambda: dt.datetime.now(dt.timezone.utc)

# ----------------------------------------------------------------------------
# Instruments
# ----------------------------------------------------------------------------
# Core sleeves: the six places the plan can put money. "sym" drives the signals.
CORE = {
    "us":     {"sym": "VTI",     "label": "US stocks",            "ppy": 252},
    "intl":   {"sym": "VXUS",    "label": "International stocks", "ppy": 252},
    "bonds":  {"sym": "BND",     "label": "Bonds",                "ppy": 252},
    "cash":   {"sym": "SGOV",    "label": "Cash and T-bills",     "ppy": 252},
    "gold":   {"sym": "IAU",     "label": "Gold",                 "ppy": 252},
    "crypto": {"sym": "BTC-USD", "label": "Crypto",               "ppy": 365},
}

# symbol -> (display name, group, periods per year)
UNIVERSE = {
    # broad US
    "VTI": ("US total market", "stocks", 252), "SPY": ("S&P 500", "stocks", 252),
    "QQQ": ("Nasdaq 100", "stocks", 252), "IWM": ("US small caps", "stocks", 252),
    "RSP": ("S&P 500 equal weight", "stocks", 252),
    # international
    "VXUS": ("International total", "stocks", 252), "VEA": ("Developed ex-US", "stocks", 252),
    "VWO": ("Emerging markets", "stocks", 252),
    # bonds and cash
    "BND": ("US bond market", "bonds", 252), "SHY": ("1-3 yr Treasuries", "bonds", 252),
    "IEF": ("7-10 yr Treasuries", "bonds", 252), "TLT": ("20+ yr Treasuries", "bonds", 252),
    "TIP": ("Inflation-linked bonds", "bonds", 252), "LQD": ("Investment-grade credit", "bonds", 252),
    "HYG": ("High-yield credit", "bonds", 252), "SGOV": ("0-3 mo T-bills", "bonds", 252),
    # real assets
    "IAU": ("Gold", "real", 252), "DBC": ("Broad commodities", "real", 252),
    "VNQ": ("US real estate", "real", 252), "CL=F": ("Crude oil (WTI)", "real", 252),
    # sectors
    "XLK": ("Technology", "sector", 252), "XLC": ("Communication", "sector", 252),
    "XLY": ("Consumer discretionary", "sector", 252), "XLF": ("Financials", "sector", 252),
    "XLI": ("Industrials", "sector", 252), "XLV": ("Health care", "sector", 252),
    "XLP": ("Consumer staples", "sector", 252), "XLE": ("Energy", "sector", 252),
    "XLU": ("Utilities", "sector", 252), "XLB": ("Materials", "sector", 252),
    "XLRE": ("Real estate", "sector", 252),
    # rates, volatility, currencies (levels, not investable here)
    "^IRX": ("3-month T-bill yield", "rate", 252), "^FVX": ("5-year Treasury yield", "rate", 252),
    "^TNX": ("10-year Treasury yield", "rate", 252), "^TYX": ("30-year Treasury yield", "rate", 252),
    "^VIX": ("VIX volatility index", "vol", 252),
    "DX-Y.NYB": ("US dollar index", "fx", 252), "EURUSD=X": ("Euro / US dollar", "fx", 260),
    "JPY=X": ("US dollar / yen", "fx", 260),
    # crypto
    "BTC-USD": ("Bitcoin", "crypto", 365), "ETH-USD": ("Ether", "crypto", 365),
    "SOL-USD": ("Solana", "crypto", 365),
}
# Symbols where we want dividend-adjusted (total return) history for fair comparisons.
TOTAL_RETURN = ["VTI", "VXUS", "BND", "SGOV", "IAU", "HYG", "IEF", "TLT", "TIP", "VNQ"]
SECTORS = ["XLK", "XLC", "XLY", "XLF", "XLI", "XLV", "XLP", "XLE", "XLU", "XLB", "XLRE"]

NEWS_QUERIES = [
    ("markets", "stock market today"),
    ("fed", "Federal Reserve OR inflation OR \"Treasury yields\""),
    ("economy", "economy jobs report OR GDP OR recession OR consumer"),
    ("earnings", "earnings results shares"),
    ("world", "oil prices OR tariffs OR sanctions OR geopolitical markets"),
    ("crypto", "bitcoin OR ethereum OR crypto market"),
]

# Headline triage. Outlets with their own newsrooms rank first; pages that are
# mostly automated filings, price tickers or prediction pages are dropped.
NEWS_PREFERRED = ("reuters", "bloomberg", "wall street journal", "wsj", "financial times", "associated press",
                  "ap news", "cnbc", "barron", "marketwatch", "axios", "the economist", "new york times",
                  "washington post", "yahoo finance", "morningstar", "pbs", "npr", "bbc", "the block",
                  "coindesk", "fortune", "politico", "the guardian", "investopedia", "kiplinger")
NEWS_DROP_SOURCES = ("marketbeat", "quiver quantitative", "simply wall st", "stock titan", "marketscreener",
                     "robinhood", "tipranks", "benzinga", "zacks", "investing.com", "tradingview",
                     "globenewswire", "pr newswire", "business wire", "accesswire", "coinpedia",
                     "cryptoticker", "ambcrypto", "crypto briefing", "tradingnews")
NEWS_DROP_TITLE = re.compile(r"price prediction|prediction market|releases? q\d|earnings results|"
                             r"issues? (quarterly )?earnings|stocks? to (buy|watch)|options volume|"
                             r"how to play|trade setup|price on nov|price target", re.I)

LAST_HALVING = dt.date(2024, 4, 20)  # fourth Bitcoin halving


def headline_rank(item):
    """0 = keep and prefer, 1 = keep, None = drop."""
    src = (item.get("src") or "").lower()
    if any(s in src for s in NEWS_DROP_SOURCES) or NEWS_DROP_TITLE.search(item.get("title") or ""):
        return None
    return 0 if any(s in src for s in NEWS_PREFERRED) else 1

# ----------------------------------------------------------------------------
# HTTP
# ----------------------------------------------------------------------------
_last_hit = {}


def http_get(url, tries=5, base_delay=2.5, timeout=45, accept="application/json"):
    """GET with per-host pacing and exponential backoff. Raises after `tries`."""
    host = urllib.parse.urlsplit(url).netloc
    err = None
    for attempt in range(tries):
        wait = 0.6 - (time.time() - _last_hit.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        _last_hit[host] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            err = "HTTP %s" % e.code
            if e.code in (400, 401, 403, 404, 410, 418):
                break  # the feed is refusing or the resource is gone: do not hammer it
        except Exception as e:  # timeouts, resets
            err = "%s: %s" % (type(e).__name__, str(e)[:80])
        time.sleep(base_delay * (2 ** attempt) + random.uniform(0, 1.0))
    raise RuntimeError("%s -> %s" % (host, err))


def get_json(url, **kw):
    return json.loads(http_get(url, **kw).decode("utf-8", "replace"))


# ----------------------------------------------------------------------------
# Small numeric helpers (pure; covered by test_refresh.py)
# ----------------------------------------------------------------------------
def clamp(x, lo=-1.0, hi=1.0):
    return max(lo, min(hi, x))


def soft(x, band):
    """Map a reading to [-1, 1], reaching the ends at +/- band. Softens flip-flops near zero."""
    if x is None:
        return None
    if band <= 0:
        return 1.0 if x > 0 else (-1.0 if x < 0 else 0.0)
    return clamp(x / band)


def sma(series, k):
    if series is None or len(series) < k:
        return None
    return sum(series[-k:]) / k


def pct(a, b):
    """Return a/b - 1, or None when it cannot be computed."""
    if a is None or b is None or b == 0:
        return None
    return a / b - 1.0


def ret(series, k):
    if series is None or len(series) <= k:
        return None
    return pct(series[-1], series[-1 - k])


def realized_vol(series, k, ppy):
    """Annualised standard deviation of daily log returns over the last k bars."""
    if series is None or len(series) <= k:
        return None
    tail = series[-(k + 1):]
    lr = [math.log(tail[i + 1] / tail[i]) for i in range(k) if tail[i] > 0 and tail[i + 1] > 0]
    if len(lr) < 2:
        return None
    m = sum(lr) / len(lr)
    var = sum((x - m) ** 2 for x in lr) / (len(lr) - 1)
    return math.sqrt(var) * math.sqrt(ppy)


def pearson(x, y):
    """Correlation of two equal-length lists, or None when it is undefined."""
    n = len(x)
    if n != len(y) or n < 3:
        return None
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx <= 0 or syy <= 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(sxx * syy)


def weekly_log_returns(named, step=5):
    """Non-overlapping log returns on the dates every series shares.

    named: {key: (dates, values)}. Stocks trade five days a week and crypto
    seven, so everything is first aligned to common dates and then sampled
    every `step` of them (about a week). Weekly sampling also keeps markets
    that close at different hours from looking less related than they are.
    Returns ({key: [returns]}, first_date, last_date).
    """
    keys = list(named)
    if not keys:
        return {}, None, None
    common = sorted(set.intersection(*[set(named[k][0]) for k in keys]))
    picks = common[::-1][::step][::-1]          # anchor on the most recent date
    out = {}
    for k in keys:
        m = dict(zip(named[k][0], named[k][1]))
        v = [m[d] for d in picks]
        out[k] = [math.log(v[i + 1] / v[i]) for i in range(len(v) - 1) if v[i] > 0 and v[i + 1] > 0]
    if not picks:
        return out, None, None
    return out, picks[0], picks[-1]


def risk_table(named, step=5, periods_per_year=52):
    """Annualised volatility and the correlation matrix for the named series."""
    rets, d0, d1 = weekly_log_returns(named, step)
    keys = list(rets)
    n = min((len(rets[k]) for k in keys), default=0)
    if n < 26:
        return None
    vol, corr = {}, {}
    for k in keys:
        r = rets[k][-n:]
        m = sum(r) / n
        vol[k] = round(math.sqrt(sum((x - m) ** 2 for x in r) / (n - 1)) * math.sqrt(periods_per_year), 4)
    for a in keys:
        corr[a] = {}
        for b in keys:
            c = 1.0 if a == b else pearson(rets[a][-n:], rets[b][-n:])
            corr[a][b] = None if c is None else round(c, 3)
    return {"from": d0, "to": d1, "weeks": n, "vol": vol, "corr": corr}


def percentile_rank(series, value):
    """Share of observations at or below value, 0..100."""
    if not series or value is None:
        return None
    return 100.0 * sum(1 for x in series if x <= value) / len(series)


def downsample(series, n):
    """Pick n evenly spaced points ending on the last one."""
    if series is None:
        return None
    if len(series) <= n:
        return list(series)
    step = (len(series) - 1) / (n - 1)
    return [series[int(round(i * step))] for i in range(n)]


def rnd(x, nd=4):
    if x is None or isinstance(x, bool):
        return x
    if isinstance(x, float):
        if math.isnan(x) or math.isinf(x):
            return None
        return round(x, nd)
    return x


def sig(x, digits=5):
    """Round to significant digits so both 0.065 and 71000 keep useful precision."""
    if x is None or x == 0:
        return x
    return round(x, max(0, digits - 1 - int(math.floor(math.log10(abs(x))))))


def label_for(score):
    if score is None:
        return "No reading"
    if score >= 0.5:
        return "Favorable"
    if score >= 0.15:
        return "Leaning positive"
    if score > -0.15:
        return "Neutral"
    if score > -0.5:
        return "Leaning negative"
    return "Unfavorable"


# ----------------------------------------------------------------------------
# Series analysis
# ----------------------------------------------------------------------------
def analyze(dates, px, tr=None, ppy=252):
    """Indicators for one instrument.

    px  display closes (what a quote screen shows)
    tr  total-return closes (dividends reinvested) when we have them, else px
    """
    tr = tr if tr and len(tr) == len(px) else px
    k1w, k1m, k3m, k6m, k12m = (max(1, round(ppy / 52)), round(ppy / 12), round(ppy / 4),
                                round(ppy / 2), ppy)
    last = px[-1]
    out = {
        "px": sig(last, 6),
        "asOf": dates[-1],
        "chg1d": rnd(ret(px, 1)),
        "ret1w": rnd(ret(tr, k1w)), "ret1m": rnd(ret(tr, k1m)), "ret3m": rnd(ret(tr, k3m)),
        "ret6m": rnd(ret(tr, k6m)), "ret12m": rnd(ret(tr, k12m)),
    }
    # year to date, from the last close of the previous calendar year
    year = dates[-1][:4]
    prev = [i for i, d in enumerate(dates) if d[:4] < year]
    out["ytd"] = rnd(pct(tr[-1], tr[prev[-1]])) if prev else None
    s50, s200 = sma(tr, 50), sma(tr, 200)
    out["vs50"] = rnd(pct(tr[-1], s50))
    out["vs200"] = rnd(pct(tr[-1], s200))
    out["cross"] = rnd(pct(s50, s200))
    s200_prev = sma(tr[:-k1m], 200) if len(tr) > 200 + k1m else None
    out["slope200"] = rnd(pct(s200, s200_prev))
    hi = max(px[-k12m:]) if len(px) >= 30 else None
    out["dd52"] = rnd(pct(last, hi))
    out["vol20"] = rnd(realized_vol(tr, 20, ppy))
    out["vol60"] = rnd(realized_vol(tr, 60, ppy))
    out["spark"] = [sig(v, 5) for v in downsample(px[-k3m:], 48)]
    return out


def trend_parts(a, cash12m, ppy=252):
    """Four trend readings for one instrument, each scored in [-1, 1].

    The mix follows the long-run evidence on trend and absolute momentum:
    a 10-month/200-day moving-average filter (Faber 2007), 12-month return in
    excess of T-bills (Moskowitz, Ooi and Pedersen 2012; Antonacci 2014), with
    a medium-term cross and 3-month return as confirmation. Bands scale with the
    instrument's own volatility so a 2% move means more for bonds than Bitcoin.
    """
    vol = a.get("vol60") or a.get("vol20") or 0.15
    parts = []

    def add(pid, label, value, band, weight, text):
        s = soft(value, band)
        parts.append({"id": pid, "label": label, "score": rnd(s, 3), "weight": weight,
                      "value": rnd(value), "text": text})

    v = a.get("vs200")
    add("vs200", "Price vs 200-day average", v, max(0.01, 0.25 * vol), 0.40,
        "n/a" if v is None else "%s the 200-day average" % (("%.1f%% above" % (v * 100)) if v >= 0 else ("%.1f%% below" % (-v * 100))))
    r12 = a.get("ret12m")
    ex = None if r12 is None or cash12m is None else r12 - cash12m
    add("mom12", "12-month return vs T-bills", ex, max(0.02, 0.5 * vol), 0.25,
        "n/a" if ex is None else "%+.1f%% over 12 months, %s T-bills by %.1f pts" % (r12 * 100, "ahead of" if ex >= 0 else "behind", abs(ex) * 100))
    c = a.get("cross")
    add("cross", "50-day vs 200-day average", c, max(0.005, 0.15 * vol), 0.20,
        "n/a" if c is None else "50-day average is %.1f%% %s the 200-day" % (abs(c) * 100, "above" if c >= 0 else "below"))
    r3 = a.get("ret3m")
    add("mom3", "3-month return", r3, max(0.01, 0.25 * vol), 0.15,
        "n/a" if r3 is None else "%+.1f%% over 3 months" % (r3 * 100))
    return parts


def combine(parts):
    """Weighted mean of the parts that have a reading; None if nothing does."""
    live = [p for p in parts if p.get("score") is not None]
    w = sum(p["weight"] for p in live)
    if not live or w <= 0:
        return None
    return clamp(sum(p["score"] * p["weight"] for p in live) / w)


# ----------------------------------------------------------------------------
# Feeds
# ----------------------------------------------------------------------------
def yahoo_spark(symbols, rng="2y", interval="1d"):
    """Batched closes: {symbol: (dates, closes, meta)}. One request per ~10 symbols."""
    out = {}
    hosts = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]
    for i in range(0, len(symbols), 10):
        chunk = symbols[i:i + 10]
        q = urllib.parse.quote(",".join(chunk))
        data, err = None, None
        for h in hosts:
            try:
                data = get_json("https://%s/v7/finance/spark?symbols=%s&range=%s&interval=%s" % (h, q, rng, interval))
                break
            except Exception as e:
                err = e
        if data is None:
            print("  yahoo spark chunk failed: %s (%s)" % (",".join(chunk), err), file=sys.stderr)
            continue
        for r in (data.get("spark", {}).get("result") or []):
            try:
                resp = r["response"][0]
                ts = resp.get("timestamp") or []
                cl = resp["indicators"]["quote"][0]["close"]
                pairs = [(t, c) for t, c in zip(ts, cl) if c is not None and c > 0]
                if len(pairs) < 30:
                    continue
                dates = [dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d") for t, _ in pairs]
                out[r["symbol"]] = (dates, [float(c) for _, c in pairs], resp.get("meta", {}))
            except Exception:
                continue
    return out


def yahoo_adjclose(symbol, rng="2y"):
    """Dividend-adjusted daily closes for one symbol: (dates, close, adjclose)."""
    q = urllib.parse.quote(symbol)
    last = None
    for h in ("query2.finance.yahoo.com", "query1.finance.yahoo.com"):
        try:
            d = get_json("https://%s/v8/finance/chart/%s?range=%s&interval=1d&events=div" % (h, q, rng), tries=4)
            res = d["chart"]["result"][0]
            ts = res["timestamp"]
            cl = res["indicators"]["quote"][0]["close"]
            adj = res["indicators"]["adjclose"][0]["adjclose"]
            rows = [(t, c, a) for t, c, a in zip(ts, cl, adj) if c and a]
            dates = [dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d") for t, _, _ in rows]
            return dates, [float(c) for _, c, _ in rows], [float(a) for _, _, a in rows]
        except Exception as e:
            last = e
    raise RuntimeError("adjclose %s: %s" % (symbol, last))


def multpl_table(slug, n=40):
    """Latest rows of a multpl.com monthly table as [(date, float)], newest first."""
    t = http_get("https://www.multpl.com/%s/table/by-month" % slug, accept="text/html").decode("utf-8", "replace")
    rows = re.findall(r"<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>", t, re.S)
    out = []
    for a, b in rows[:n]:
        a = re.sub(r"<[^>]+>", "", a).strip()
        b = html.unescape(re.sub(r"<[^>]+>", "", b))
        m = re.search(r"-?\d+(?:\.\d+)?", b.replace(",", ""))
        try:
            d = dt.datetime.strptime(a, "%b %d, %Y").date()
        except ValueError:
            continue
        if m:
            out.append((d.isoformat(), float(m.group(0))))
    return out


def multpl_history(slug):
    """Every monthly value of a multpl table, oldest first (for percentile ranks)."""
    t = http_get("https://www.multpl.com/%s/table/by-month" % slug, accept="text/html").decode("utf-8", "replace")
    rows = re.findall(r"<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>", t, re.S)
    vals = []
    for a, b in rows:
        b = html.unescape(re.sub(r"<[^>]+>", "", b))
        m = re.search(r"-?\d+(?:\.\d+)?", b.replace(",", ""))
        a = re.sub(r"<[^>]+>", "", a).strip()
        try:
            d = dt.datetime.strptime(a, "%b %d, %Y").date()
        except ValueError:
            continue
        if m:
            vals.append((d.isoformat(), float(m.group(0))))
    vals.sort()
    return vals


def google_news(query, when="1d", limit=14):
    url = "https://news.google.com/rss/search?q=%s&hl=en-US&gl=US&ceid=US:en" % urllib.parse.quote("%s when:%s" % (query, when))
    root = ET.fromstring(http_get(url, accept="application/rss+xml"))
    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        src = (it.findtext("source") or "").strip()
        if src and title.endswith(" - " + src):
            title = title[: -len(src) - 3].strip()
        try:
            t = dt.datetime.strptime(it.findtext("pubDate") or "", "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
        items.append({"t": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "title": title[:220], "src": src[:60],
                      "url": (it.findtext("link") or "").strip()})
    items.sort(key=lambda x: x["t"], reverse=True)
    return items[:limit]


# ----------------------------------------------------------------------------
# Build
# ----------------------------------------------------------------------------
def build(out_dir, verbose=True):
    log = (lambda *a: print(*a, file=sys.stderr)) if verbose else (lambda *a: None)
    sources = {}

    def source(name, fn, note):
        t0 = time.time()
        try:
            v = fn()
            sources[name] = {"ok": True, "note": note, "at": NOW().strftime("%Y-%m-%dT%H:%M:%SZ")}
            log("ok   %-12s %.1fs" % (name, time.time() - t0))
            return v
        except Exception as e:
            sources[name] = {"ok": False, "note": note, "error": str(e)[:160]}
            log("FAIL %-12s %s" % (name, str(e)[:160]))
            return None

    # ---- prices -------------------------------------------------------------
    symbols = list(UNIVERSE.keys())
    spark = source("prices", lambda: yahoo_spark(symbols), "Yahoo Finance daily closes, 2 years") or {}
    missing = [s for s in symbols if s not in spark]
    if missing and spark:
        log("  retrying %d missing symbols" % len(missing))
        time.sleep(4)
        spark.update(yahoo_spark(missing))
    if not spark:
        raise SystemExit("No price data could be fetched; refusing to write an empty snapshot.")

    tr_series = {}

    def fetch_tr():
        got = 0
        for s in TOTAL_RETURN:
            try:
                d, c, a = yahoo_adjclose(s)
                tr_series[s] = (d, c, a)
                got += 1
            except Exception as e:
                log("  no total-return series for %s (%s)" % (s, str(e)[:80]))
        if not got:
            raise RuntimeError("no adjusted series")
        return got
    source("totalReturn", fetch_tr, "Yahoo Finance dividend-adjusted closes for the core funds")

    weekly = source("weekly", lambda: yahoo_spark(["BTC-USD", "^GSPC"], rng="10y", interval="1wk"),
                    "Yahoo Finance weekly closes, 10 years") or {}

    assets = {}
    series = {}  # symbol -> (dates, px, tr)
    for s, (name, group, ppy) in UNIVERSE.items():
        if s in tr_series:
            d, c, a = tr_series[s]
            # splice in the freshest quote from the batched feed
            if s in spark and spark[s][0][-1] >= d[-1]:
                live = spark[s][1][-1]
                if spark[s][0][-1] == d[-1]:
                    a = a[:-1] + [a[-1] * live / c[-1]]
                    c = c[:-1] + [live]
            series[s] = (d, c, a)
            total = True
        elif s in spark:
            d, c, _ = spark[s]
            series[s] = (d, c, None)
            total = False
        else:
            continue
        d, c, a = series[s]
        info = analyze(d, c, a, ppy)
        info.update({"name": name, "group": group, "totalReturn": total})
        assets[s] = info

    def A(sym, key=None):
        a = assets.get(sym)
        return a if key is None or a is None else a.get(key)

    # ---- macro levels -------------------------------------------------------
    macro = {}
    for k, s in (("y3m", "^IRX"), ("y5y", "^FVX"), ("y10y", "^TNX"), ("y30y", "^TYX"), ("vix", "^VIX"), ("dxy", "DX-Y.NYB")):
        if s in series:
            macro[k] = rnd(series[s][1][-1], 3)
    if "^TNX" in series and len(series["^TNX"][1]) > 63:
        macro["y10yChg3m"] = rnd(series["^TNX"][1][-1] - series["^TNX"][1][-64], 3)
        macro["y10yHi52"] = rnd(max(series["^TNX"][1][-252:]), 3)
    if "^IRX" in series and len(series["^IRX"][1]) > 63:
        macro["y3mChg3m"] = rnd(series["^IRX"][1][-1] - series["^IRX"][1][-64], 3)
    if "y10y" in macro and "y3m" in macro:
        macro["curve"] = rnd(macro["y10y"] - macro["y3m"], 3)
    if "^VIX" in series:
        v = series["^VIX"][1]
        macro["vixPct"] = rnd(percentile_rank(v[-504:], v[-1]), 0)
        macro["vixAvg1y"] = rnd(sum(v[-252:]) / len(v[-252:]), 2)
    macro["dxyVs200"] = A("DX-Y.NYB", "vs200")

    def fetch_valuation():
        cape_hist = multpl_history("shiller-pe")
        cape = cape_hist[-1][1]
        macro["cape"] = cape
        macro["capeAsOf"] = cape_hist[-1][0]
        macro["capePct"] = rnd(percentile_rank([v for _, v in cape_hist], cape), 0)
        since = [v for d, v in cape_hist if d >= "1990-01-01"]
        macro["capePctSince1990"] = rnd(percentile_rank(since, cape), 0)
        macro["capeMedian"] = rnd(sorted(v for _, v in cape_hist)[len(cape_hist) // 2], 1)
        pe = multpl_table("s-p-500-pe-ratio", 3)
        if pe:
            macro["pe"] = pe[0][1]
            macro["earnYield"] = rnd(100.0 / pe[0][1], 2)
        dy = multpl_table("s-p-500-dividend-yield", 3)
        if dy:
            macro["divYield"] = dy[0][1]
        return True
    source("valuation", fetch_valuation, "multpl.com: Shiller CAPE, S&P 500 P/E and dividend yield")

    def fetch_inflation():
        rows = multpl_table("inflation", 16)
        macro["cpi"] = rows[0][1]
        macro["cpiAsOf"] = rows[0][0][:7]
        macro["cpi3mAgo"] = rows[3][1]
        macro["cpi12mAgo"] = rows[12][1]
        macro["cpiTrail"] = [r[1] for r in rows[:13]][::-1]
        return True
    source("inflation", fetch_inflation, "multpl.com: US CPI inflation, year over year (BLS data)")

    if macro.get("earnYield") is not None and macro.get("y10y") is not None:
        macro["erp"] = rnd(macro["earnYield"] - macro["y10y"], 2)  # earnings yield minus 10-year yield
    if macro.get("y3m") is not None and macro.get("cpi") is not None:
        macro["realCash"] = rnd(macro["y3m"] - macro["cpi"], 2)
    if macro.get("y5y") is not None and macro.get("cpi") is not None:
        macro["realBond"] = rnd(macro["y5y"] - macro["cpi"], 2)

    # ---- risk regime --------------------------------------------------------
    regime_parts = []

    def rpart(pid, label, score, weight, text):
        regime_parts.append({"id": pid, "label": label, "score": rnd(score, 3), "weight": weight, "text": text})

    # credit: high-yield bonds against 7-10 year Treasuries (total return)
    credit = None
    if "HYG" in series and "IEF" in series:
        dh, _, ah = series["HYG"]
        di, _, ai = series["IEF"]
        ah = ah or series["HYG"][1]
        ai = ai or series["IEF"][1]
        common = sorted(set(dh) & set(di))
        mh, mi = dict(zip(dh, ah)), dict(zip(di, ai))
        ratio = [mh[d] / mi[d] for d in common]
        if len(ratio) > 200:
            vs = pct(ratio[-1], sma(ratio, 200))
            ch = ret(ratio, 63)
            credit = clamp(0.6 * soft(vs, 0.03) + 0.4 * soft(ch, 0.03))
            macro["creditVs200"] = rnd(vs)
            macro["credit3m"] = rnd(ch)
            rpart("credit", "Credit markets", credit, 0.35,
                  "High-yield bonds are %.1f%% %s their 200-day trend against Treasuries (%+.1f%% over 3 months)" %
                  (abs(vs) * 100, "above" if vs >= 0 else "below", ch * 100))
    if credit is None:
        rpart("credit", "Credit markets", None, 0.35, "No reading")

    vix = macro.get("vix")
    if vix is not None:
        vs_ = 0.6 if vix < 14 else 0.35 if vix < 17 else 0.0 if vix < 21 else -0.5 if vix < 28 else -1.0
        band = "calm" if vix < 17 else "normal" if vix < 21 else "elevated" if vix < 28 else "stressed"
        rpart("vix", "Expected volatility", vs_, 0.30, "VIX at %.1f, %s (1-year average %.1f)" % (vix, band, macro.get("vixAvg1y") or float("nan")))
    else:
        rpart("vix", "Expected volatility", None, 0.30, "No reading")

    above = [s for s in SECTORS if (A(s, "vs200") or 0) > 0]
    have = [s for s in SECTORS if A(s, "vs200") is not None]
    if have:
        share = len(above) / len(have)
        macro["breadth"] = rnd(share, 2)
        rel = None
        if A("RSP", "ret3m") is not None and A("SPY", "ret3m") is not None:
            rel = A("RSP", "ret3m") - A("SPY", "ret3m")
            macro["equalWeightRel3m"] = rnd(rel)
        b = clamp((share - 0.5) * 2.0)
        text = "%d of %d sectors are above their 200-day average" % (len(above), len(have))
        if rel is not None:
            text += "; the average stock is %s the index by %.1f pts over 3 months" % ("beating" if rel >= 0 else "lagging", abs(rel) * 100)
        rpart("breadth", "Market breadth", b, 0.20, text)
    else:
        rpart("breadth", "Market breadth", None, 0.20, "No reading")

    curve = macro.get("curve")
    if curve is not None:
        cs = clamp(curve / 1.5) if curve < 0 else clamp(curve / 2.0, 0, 0.5)
        rpart("curve", "Yield curve", cs, 0.15,
              "10-year yield is %.2f pts %s the 3-month bill%s" % (abs(curve), "above" if curve >= 0 else "below",
                                                                  "" if curve >= 0 else " (inverted: a classic recession warning)"))
    else:
        rpart("curve", "Yield curve", None, 0.15, "No reading")

    regime_score = combine(regime_parts)
    regime = {"score": rnd(regime_score, 3), "label": label_for(regime_score), "parts": regime_parts}

    # ---- sleeves ------------------------------------------------------------
    cash12m = A("SGOV", "ret12m")
    if cash12m is None and macro.get("y3m") is not None:
        cash12m = macro["y3m"] / 100.0
    macro["cash12m"] = rnd(cash12m)

    def trend_block(sym, ppy=252):
        a = assets.get(sym)
        if not a:
            return None, []
        parts = trend_parts(a, cash12m, ppy)
        return combine(parts), parts

    sleeves = {}

    def sleeve(key, parts):
        score = combine(parts)
        sleeves[key] = {"label": CORE[key]["label"], "sym": CORE[key]["sym"], "score": rnd(score, 3),
                        "stance": label_for(score), "parts": parts}

    def P(pid, label, score, weight, text, detail=None):
        d = {"id": pid, "label": label, "score": rnd(score, 3), "weight": weight, "text": text}
        if detail:
            d["detail"] = detail
        return d

    def trend_text(sym, score):
        a = assets.get(sym) or {}
        v = a.get("vs200")
        if v is None:
            return "No reading"
        return "%s is %.1f%% %s its 200-day average; 12-month return %s" % (
            UNIVERSE[sym][0], abs(v) * 100, "above" if v >= 0 else "below",
            "n/a" if a.get("ret12m") is None else "%+.1f%%" % (a["ret12m"] * 100))

    risk_text = "Credit, volatility, breadth and the yield curve together read %s" % regime["label"].lower()
    dxy_vs = macro.get("dxyVs200")
    dollar_score = None if dxy_vs is None else -soft(dxy_vs, 0.03)  # a weaker dollar helps non-US assets and gold
    dollar_text = "No reading" if dxy_vs is None else "US dollar index is %.1f%% %s its 200-day average" % (abs(dxy_vs) * 100, "above" if dxy_vs >= 0 else "below")

    # US stocks
    us_t, us_tp = trend_block("VTI")
    cape, erp = macro.get("cape"), macro.get("erp")
    val_score, val_text = None, "No reading"
    if cape is not None:
        v1 = clamp((25.0 - cape) / 15.0)          # CAPE 25 is neutral, 40+ fully stretched, 10 fully cheap
        v2 = clamp(erp / 3.0) if erp is not None else None  # +3 pts of earnings yield over bonds is generous
        val_score = v1 if v2 is None else clamp(0.6 * v1 + 0.4 * v2)
        val_text = "Shiller P/E is %.1f (higher than %s%% of months since 1881)" % (cape, int(macro.get("capePct") or 0))
        if erp is not None:
            val_text += "; stocks' earnings yield is %.1f pts %s the 10-year Treasury" % (abs(erp), "above" if erp >= 0 else "below")
    sleeve("us", [
        P("trend", "Trend", us_t, 0.50, trend_text("VTI", us_t), us_tp),
        P("risk", "Risk conditions", regime_score, 0.30, risk_text),
        P("value", "Valuation", val_score, 0.20, val_text),
    ])

    # International stocks
    in_t, in_tp = trend_block("VXUS")
    sleeve("intl", [
        P("trend", "Trend", in_t, 0.60, trend_text("VXUS", in_t), in_tp),
        P("risk", "Risk conditions", regime_score, 0.25, risk_text),
        P("dollar", "US dollar", dollar_score, 0.15, dollar_text),
    ])

    # Bonds
    bo_t, bo_tp = trend_block("BND")
    rb = macro.get("realBond")
    carry_score = None if rb is None else clamp((rb - 0.5) / 1.5)
    carry_text = "No reading" if rb is None else "5-year Treasury yields %.2f%%, which is %.1f pts %s inflation" % (
        macro["y5y"], abs(rb), "above" if rb >= 0 else "below")
    infl_score, infl_text = None, "No reading"
    if macro.get("cpi") is not None and macro.get("cpi3mAgo") is not None:
        d3 = macro["cpi"] - macro["cpi3mAgo"]
        lvl = macro["cpi"]
        # falling inflation helps bonds; high and rising inflation hurts them
        infl_score = clamp(-d3 / 0.5) * 0.7 + clamp((2.5 - lvl) / 2.0) * 0.3
        infl_score = clamp(infl_score)
        infl_text = "Inflation is %.1f%% (%s), %s %.1f%% three months earlier" % (
            lvl, macro.get("cpiAsOf"), "up from" if d3 > 0 else "down from" if d3 < 0 else "unchanged from", macro["cpi3mAgo"])
    sleeve("bonds", [
        P("trend", "Trend", bo_t, 0.45, trend_text("BND", bo_t), bo_tp),
        P("carry", "Yield after inflation", carry_score, 0.30, carry_text),
        P("inflation", "Inflation direction", infl_score, 0.25, infl_text),
    ])

    # Gold
    go_t, go_tp = trend_block("IAU")
    rr_score, rr_text = None, "No reading"
    if macro.get("y10yChg3m") is not None:
        d_infl = (macro["cpi"] - macro["cpi3mAgo"]) if macro.get("cpi") is not None and macro.get("cpi3mAgo") is not None else 0.0
        real_chg = macro["y10yChg3m"] - d_infl
        rr_score = -soft(real_chg, 0.6)  # rising real yields raise the cost of holding gold
        rr_text = "10-year yield moved %+.2f pts in 3 months against a %+.2f pt move in inflation" % (macro["y10yChg3m"], d_infl)
    sleeve("gold", [
        P("trend", "Trend", go_t, 0.65, trend_text("IAU", go_t), go_tp),
        P("real", "Real interest rates", rr_score, 0.20, rr_text),
        P("dollar", "US dollar", dollar_score, 0.15, dollar_text),
    ])

    # Cash has no trend; its appeal is its yield after inflation.
    rc = macro.get("realCash")
    sleeves["cash"] = {"label": CORE["cash"]["label"], "sym": "SGOV", "score": None, "stance": "Anchor",
                       "parts": [P("yield", "Yield", None, 1.0,
                                   "No reading" if macro.get("y3m") is None else "3-month T-bills yield %.2f%%%s" % (
                                       macro["y3m"], "" if rc is None else ", %.1f pts %s inflation" % (abs(rc), "above" if rc >= 0 else "below")))]}

    # ---- crypto -------------------------------------------------------------
    crypto = {}
    btc_t, btc_tp = trend_block("BTC-USD", 365)

    def fetch_cg():
        g = get_json("https://api.coingecko.com/api/v3/global")["data"]
        crypto["mcap"] = rnd(g["total_market_cap"]["usd"], 0)
        crypto["mcapChg24h"] = rnd(g.get("market_cap_change_percentage_24h_usd", 0) / 100.0)
        crypto["btcDom"] = rnd(g["market_cap_percentage"].get("btc"), 2)
        crypto["ethDom"] = rnd(g["market_cap_percentage"].get("eth"), 2)
        time.sleep(1.5)
        m = get_json("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1&price_change_percentage=24h,7d,30d,1y")
        top = []
        for c in m:
            sym = (c.get("symbol") or "").upper()
            px = c.get("current_price")
            if px is None:
                continue
            stable = abs(px - 1.0) < 0.06 and abs(c.get("price_change_percentage_30d_in_currency") or 0) < 3 and abs(c.get("ath_change_percentage") or 0) < 30
            top.append({"sym": sym[:10], "name": (c.get("name") or "")[:22], "px": sig(px, 5),
                        "mcap": rnd(c.get("market_cap"), 0), "stable": stable,
                        "d1": rnd((c.get("price_change_percentage_24h_in_currency") or 0) / 100), "d7": rnd((c.get("price_change_percentage_7d_in_currency") or 0) / 100),
                        "d30": rnd((c.get("price_change_percentage_30d_in_currency") or 0) / 100),
                        "y1": None if c.get("price_change_percentage_1y_in_currency") is None else rnd(c["price_change_percentage_1y_in_currency"] / 100),
                        "ath": sig(c.get("ath"), 5), "fromAth": rnd((c.get("ath_change_percentage") or 0) / 100)})
        crypto["top"] = top[:15]
        return True
    source("coingecko", fetch_cg, "CoinGecko: crypto market size, dominance and the largest coins")

    def fetch_fng():
        f = get_json("https://api.alternative.me/fng/?limit=400")["data"]
        vals = [int(x["value"]) for x in f]
        crypto["fng"] = {"now": vals[0], "label": f[0]["value_classification"], "avg7": rnd(sum(vals[:7]) / 7, 1),
                         "avg30": rnd(sum(vals[:30]) / 30, 1), "min1y": min(vals[:365]), "max1y": max(vals[:365]),
                         "trail": downsample(vals[:120][::-1], 40)}
        return True
    source("fearGreed", fetch_fng, "alternative.me: Crypto Fear and Greed Index")

    def fetch_stables():
        s = get_json("https://stablecoins.llama.fi/stablecoincharts/all", timeout=90)
        v = [x["totalCirculatingUSD"]["peggedUSD"] for x in s[-400:]]
        crypto["stables"] = {"usd": rnd(v[-1], 0), "chg30": rnd(pct(v[-1], v[-31])), "chg90": rnd(pct(v[-1], v[-91])),
                             "trail": [rnd(x / 1e9, 1) for x in downsample(v[-365:], 40)]}
        return True
    source("stablecoins", fetch_stables, "DefiLlama: dollar stablecoin supply")

    def fetch_coinbase():
        out = {}
        for p in ("BTC-USD", "ETH-USD"):
            t = get_json("https://api.exchange.coinbase.com/products/%s/ticker" % p, tries=3)
            out[p] = float(t["price"])
        crypto["spot"] = {"btc": sig(out["BTC-USD"], 6), "eth": sig(out["ETH-USD"], 6), "src": "Coinbase"}
        return True
    source("coinbase", fetch_coinbase, "Coinbase: live Bitcoin and Ether prices")

    if "BTC-USD" in assets:
        b = dict(assets["BTC-USD"])
        b.pop("spark", None)
        if "BTC-USD" in weekly and len(weekly["BTC-USD"][1]) >= 200:
            w = weekly["BTC-USD"][1]
            b["sma200w"] = sig(sma(w, 200), 6)
            b["vs200w"] = rnd(pct(w[-1], sma(w, 200)))
        top = {c["sym"]: c for c in crypto.get("top", [])}
        if "BTC" in top:
            b["ath"] = top["BTC"]["ath"]
            b["fromAth"] = top["BTC"]["fromAth"]
        d, c, _ = series["BTC-USD"]
        b["sma200"] = sig(sma(c, 200), 6)
        b["sma50"] = sig(sma(c, 50), 6)
        crypto["btc"] = b
    if "ETH-USD" in assets:
        e = dict(assets["ETH-USD"])
        e.pop("spark", None)
        top = {c["sym"]: c for c in crypto.get("top", [])}
        if "ETH" in top:
            e["ath"] = top["ETH"]["ath"]
            e["fromAth"] = top["ETH"]["fromAth"]
        crypto["eth"] = e
    if "BTC-USD" in series and "ETH-USD" in series:
        db_, cb, _ = series["BTC-USD"]
        de, ce, _ = series["ETH-USD"]
        mb, me = dict(zip(db_, cb)), dict(zip(de, ce))
        common = sorted(set(db_) & set(de))
        ratio = [me[d] / mb[d] for d in common]
        if len(ratio) > 200:
            crypto["ethBtc"] = {"now": rnd(ratio[-1], 5), "vs200": rnd(pct(ratio[-1], sma(ratio, 200))), "chg90": rnd(ret(ratio, 90))}
    days = (NOW().date() - LAST_HALVING).days
    crypto["halving"] = {"last": LAST_HALVING.isoformat(), "daysSince": days, "monthsSince": rnd(days / 30.44, 1)}

    liq_score, liq_text = None, "No reading"
    st = crypto.get("stables")
    if st and st.get("chg30") is not None:
        liq_score = clamp(0.6 * soft(st["chg30"], 0.03) + 0.4 * soft(st.get("chg90") or 0, 0.06))
        liq_text = "Stablecoin supply is $%.0fB, %+.1f%% in 30 days and %+.1f%% in 90" % (st["usd"] / 1e9, st["chg30"] * 100, (st.get("chg90") or 0) * 100)
    sent_score, sent_text = None, "No reading"
    fg = crypto.get("fng")
    if fg:
        n = fg["now"]
        # contrarian only at the extremes; the middle of the range says nothing useful
        sent_score = 0.6 if n <= 15 else 0.3 if n <= 25 else -0.3 if n >= 75 and n < 85 else -0.6 if n >= 85 else 0.0
        sent_text = "Fear and Greed Index is %d (%s); extremes tend to reverse, the middle means little" % (n, fg["label"])
    sleeve("crypto", [
        P("trend", "Bitcoin trend", btc_t, 0.55, trend_text("BTC-USD", btc_t), btc_tp),
        P("risk", "Risk conditions", regime_score, 0.20, risk_text),
        P("liquidity", "Crypto liquidity", liq_score, 0.15, liq_text),
        P("sentiment", "Sentiment (contrarian)", sent_score, 0.10, sent_text),
    ])

    # ---- chart series for the six sleeves -----------------------------------
    charts = {}
    for key, c in CORE.items():
        s = c["sym"]
        if s not in series:
            continue
        d, px, tr = series[s]
        tr = tr or px
        n = min(len(tr) - 199, c["ppy"]) if len(tr) > 230 else 0
        if n <= 30:
            continue
        idx = list(range(len(tr) - n, len(tr)))
        ma = [sum(tr[i - 199:i + 1]) / 200 for i in idx]
        base = tr[idx[0]]
        pick = downsample(list(range(n)), 90)
        charts[key] = {"sym": s, "from": d[idx[0]], "to": d[-1],
                       "dates": [d[idx[i]] for i in pick],
                       "px": [rnd(tr[idx[i]] / base * 100, 2) for i in pick],
                       "ma": [rnd(ma[i] / base * 100, 2) for i in pick]}

    # ---- how the six parts move together -------------------------------------
    named = {}
    for key, c in CORE.items():
        if c["sym"] in series:
            d, px, tr = series[c["sym"]]
            named[key] = (d, tr or px)
    risk = risk_table(named) if len(named) == len(CORE) else None

    # ---- headlines ----------------------------------------------------------
    headlines_full = []

    def fetch_news():
        seen = set()
        for topic, q in NEWS_QUERIES:
            try:
                items = google_news(q)
            except Exception as e:
                log("  news '%s' failed: %s" % (topic, str(e)[:80]))
                continue
            for it in items:
                key = re.sub(r"[^a-z0-9]+", "", it["title"].lower())[:60]
                if key in seen or not it["title"]:
                    continue
                seen.add(key)
                it["topic"] = topic
                headlines_full.append(it)
        if not headlines_full:
            raise RuntimeError("no headlines")
        headlines_full.sort(key=lambda x: x["t"], reverse=True)
        return True
    source("news", fetch_news, "Google News: headlines from the last 24 hours")

    # A short list for the page: drop low-signal pages, prefer outlets with
    # newsrooms, keep at most 4 per topic, newest first.
    ranked = [(headline_rank(h), h) for h in headlines_full]
    pool = sorted([(r, h) for r, h in ranked if r is not None], key=lambda x: x[0])  # stable: stays newest-first within rank
    per, short = {}, []
    for _, h in pool:
        if per.get(h["topic"], 0) >= 4:
            continue
        per[h["topic"]] = per.get(h["topic"], 0) + 1
        short.append(h)
    short = sorted(short[:20], key=lambda x: x["t"], reverse=True)

    # ---- assemble -----------------------------------------------------------
    spy = assets.get("SPY") or assets.get("VTI") or {}
    ny = NOW() - dt.timedelta(hours=5)  # close enough for an "is the market open" hint
    is_open = ny.weekday() < 5 and (9, 30) <= (ny.hour, ny.minute) < (16, 0)
    quote_at = None
    try:
        qt = (spark.get("SPY") or spark.get("VTI"))[2].get("regularMarketTime")
        quote_at = dt.datetime.fromtimestamp(qt, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass
    snapshot = {
        "v": 1,
        "generatedAt": NOW().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pricesAsOf": spy.get("asOf"),
        "quoteAt": quote_at,
        "usMarketHours": is_open,
        "assets": assets,
        "macro": macro,
        "regime": regime,
        "sleeves": sleeves,
        "charts": charts,
        "risk": risk,
        "crypto": crypto,
        "sectors": SECTORS,
        "headlines": short,
        "sources": sources,
    }
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "snapshot.json"), "w") as f:
        json.dump(snapshot, f, separators=(",", ":"))
    with open(os.path.join(out_dir, "headlines.json"), "w") as f:
        json.dump({"generatedAt": snapshot["generatedAt"], "headlines": headlines_full}, f, indent=1)
    return snapshot


def summary(s):
    """A plain-text digest for whoever writes the news brief."""
    L = []
    m = s["macro"]
    L.append("Market Compass snapshot  %s  (prices as of %s)" % (s["generatedAt"], s["pricesAsOf"]))
    L.append("")
    L.append("%-22s %10s %7s %7s %7s %7s %8s" % ("Asset", "Price", "1d", "1m", "3m", "12m", "vs200d"))
    order = ["SPY", "QQQ", "IWM", "VXUS", "VWO", "BND", "TLT", "TIP", "HYG", "IAU", "CL=F", "DBC", "VNQ", "BTC-USD", "ETH-USD", "SOL-USD", "DX-Y.NYB"]
    f = lambda x: "   n/a" if x is None else "%+6.1f%%" % (x * 100)
    for k in order:
        a = s["assets"].get(k)
        if a:
            L.append("%-22s %10s %7s %7s %7s %7s %8s" % (a["name"][:22], a["px"], f(a["chg1d"]), f(a["ret1m"]), f(a["ret3m"]), f(a["ret12m"]), f(a["vs200"])))
    L.append("")
    L.append("Rates: 3m %s  5y %s  10y %s  30y %s | curve 10y-3m %s | 10y 3m change %s" % (m.get("y3m"), m.get("y5y"), m.get("y10y"), m.get("y30y"), m.get("curve"), m.get("y10yChg3m")))
    L.append("VIX %s (pct rank %s) | Dollar index %s (vs 200d %s)" % (m.get("vix"), m.get("vixPct"), m.get("dxy"), f(m.get("dxyVs200"))))
    L.append("Valuation: CAPE %s (pct %s) | P/E %s | earnings yield %s | ERP vs 10y %s" % (m.get("cape"), m.get("capePct"), m.get("pe"), m.get("earnYield"), m.get("erp")))
    L.append("Inflation: CPI %s%% (%s), 3m ago %s%% | real cash %s | real 5y %s" % (m.get("cpi"), m.get("cpiAsOf"), m.get("cpi3mAgo"), m.get("realCash"), m.get("realBond")))
    L.append("")
    L.append("Risk regime: %s (%s)" % (s["regime"]["label"], s["regime"]["score"]))
    for p in s["regime"]["parts"]:
        L.append("   %-22s %6s  %s" % (p["label"], p["score"], p["text"]))
    L.append("")
    for k, sl in s["sleeves"].items():
        L.append("%-22s %-18s score %s" % (sl["label"], sl["stance"], sl["score"]))
        for p in sl["parts"]:
            L.append("   %-24s w%.2f %6s  %s" % (p["label"], p["weight"], p["score"], p["text"]))
    c = s["crypto"]
    L.append("")
    if c.get("btc"):
        L.append("BTC: %s | from ATH %s | vs 200d %s | vs 200wk %s | dominance %s%%" % (c["btc"]["px"], f(c["btc"].get("fromAth")), f(c["btc"].get("vs200")), f(c["btc"].get("vs200w")), c.get("btcDom")))
    if c.get("fng"):
        L.append("Fear & Greed: %s (%s), 30d avg %s" % (c["fng"]["now"], c["fng"]["label"], c["fng"]["avg30"]))
    if c.get("stables"):
        L.append("Stablecoins: $%.0fB, 30d %s, 90d %s" % (c["stables"]["usd"] / 1e9, f(c["stables"]["chg30"]), f(c["stables"]["chg90"])))
    L.append("Halving clock: %s months since %s" % (c["halving"]["monthsSince"], c["halving"]["last"]))
    r = s.get("risk")
    if r:
        L.append("")
        L.append("Risk, %s weeks to %s: yearly swing %s" % (r["weeks"], r["to"], "  ".join("%s %.0f%%" % (k, v * 100) for k, v in r["vol"].items())))
        L.append("Correlation with US stocks: %s" % "  ".join("%s %+.2f" % (k, v) for k, v in r["corr"]["us"].items() if k != "us" and v is not None))
    L.append("")
    bad = [k for k, v in s["sources"].items() if not v["ok"]]
    L.append("Sources OK: %d/%d%s" % (len(s["sources"]) - len(bad), len(s["sources"]), ("  FAILED: " + ", ".join(bad)) if bad else ""))
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Refresh Market Compass data")
    ap.add_argument("--out", default="./out", help="directory for snapshot.json and headlines.json")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    snap = build(args.out, verbose=not args.quiet)
    print(summary(snap))
    size = os.path.getsize(os.path.join(args.out, "snapshot.json"))
    print("\nWrote %s (%.0f KB)" % (os.path.join(args.out, "snapshot.json"), size / 1024.0))
