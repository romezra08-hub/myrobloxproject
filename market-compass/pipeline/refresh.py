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
import csv
import datetime as dt
import html
import io
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
    "VWO": ("Emerging markets", "stocks", 252), "^TA125.TA": ("Tel Aviv 125", "stocks", 245),
    # bonds and cash
    "BND": ("US bond market", "bonds", 252), "SHY": ("1-3 yr Treasuries", "bonds", 252),
    "IEI": ("3-7 yr Treasuries", "bonds", 252),
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
    "JPY=X": ("US dollar / yen", "fx", 260), "ILS=X": ("US dollar / shekel", "fx", 260),
    # crypto
    "BTC-USD": ("Bitcoin", "crypto", 365), "ETH-USD": ("Ether", "crypto", 365),
    "SOL-USD": ("Solana", "crypto", 365),
}
# Symbols where we want dividend-adjusted (total return) history for fair comparisons.
TOTAL_RETURN = ["VTI", "VXUS", "BND", "SGOV", "IAU", "HYG", "IEI", "IEF", "TLT", "TIP", "VNQ"]
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
FORECAST_ASSETS = ["SPY", "^TA125.TA", "BTC-USD", "IAU", "ILS=X"]   # the same five as forecasts.py

# Well-known shares and coins from which the "hot names" are drawn: each day the five of each
# with the best twelve months. They exist only for the one-day forecasts on the Forecasts tab,
# which the owner asked for as a test. Nothing in the plan uses them.
HOT_STOCKS = {
    "NVDA": "Nvidia", "AVGO": "Broadcom", "AMD": "AMD", "TSM": "TSMC", "MU": "Micron", "PLTR": "Palantir", "TSLA": "Tesla",
    "META": "Meta", "GOOGL": "Alphabet", "AMZN": "Amazon", "MSFT": "Microsoft", "AAPL": "Apple", "NFLX": "Netflix",
    "ORCL": "Oracle", "CRWD": "CrowdStrike", "NET": "Cloudflare", "SHOP": "Shopify", "UBER": "Uber", "COIN": "Coinbase",
    "HOOD": "Robinhood", "MSTR": "Strategy", "APP": "AppLovin", "RKLB": "Rocket Lab", "IONQ": "IonQ", "SOFI": "SoFi",
    "CVNA": "Carvana", "ARM": "Arm", "SMCI": "Super Micro", "LLY": "Eli Lilly", "COST": "Costco", "JPM": "JPMorgan",
    "GE": "GE Aerospace", "VST": "Vistra", "CEG": "Constellation Energy", "ANET": "Arista", "DELL": "Dell",
    "SNOW": "Snowflake", "RBLX": "Roblox", "SPOT": "Spotify", "DASH": "DoorDash",
}
HOT_COINS = {
    "BTC-USD": "Bitcoin", "ETH-USD": "Ether", "SOL-USD": "Solana", "XRP-USD": "XRP", "BNB-USD": "BNB", "DOGE-USD": "Dogecoin",
    "ADA-USD": "Cardano", "TRX-USD": "Tron", "AVAX-USD": "Avalanche", "LINK-USD": "Chainlink", "HBAR-USD": "Hedera",
    "XLM-USD": "Stellar", "LTC-USD": "Litecoin", "BCH-USD": "Bitcoin Cash", "DOT-USD": "Polkadot", "SHIB-USD": "Shiba Inu",
    "AAVE-USD": "Aave", "NEAR-USD": "Near",
}
HOT_KEEP = ("px", "asOf", "chg1d", "ret1w", "ret1m", "ret3m", "ret12m", "vs50", "vs200", "vol20", "up1d", "up1w")


def hot_picks(table, symbols, n=5):
    """The n symbols with the best twelve months, best first. Ones with no 12-month figure are left out."""
    ranked = sorted(((table[s]["ret12m"], s) for s in symbols if s in table and table[s].get("ret12m") is not None), reverse=True)
    return [s for _, s in ranked[:n]]


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
    out["vs100"] = rnd(pct(tr[-1], sma(tr, 100)))
    out["vs200"] = rnd(pct(tr[-1], s200))
    out["cross"] = rnd(pct(s50, s200))
    s200_prev = sma(tr[:-k1m], 200) if len(tr) > 200 + k1m else None
    out["slope200"] = rnd(pct(s200, s200_prev))
    hi = max(px[-k12m:]) if len(px) >= 30 else None
    out["dd52"] = rnd(pct(last, hi))
    out["vol20"] = rnd(realized_vol(tr, 20, ppy))
    out["vol60"] = rnd(realized_vol(tr, 60, ppy))
    out["spark"] = [sig(v, 5) for v in downsample(px[-k3m:], 48)]
    # How often the price was higher a week and a month later, over the history we hold.
    # This is the naive forecast that any prediction on the Forecasts tab has to beat.
    out["up1w"], out["up1m"] = rnd(share_up(px, k1w), 3), rnd(share_up(px, k1m), 3)
    out["up1d"] = rnd(share_up(px[-(k12m + 1):], 1), 3)
    return out


def typical_range(px, vol, days, ppy=252):
    """The band a price lands in about 80% of the time after `days` calendar days, given its yearly
    swing: 1.28 standard deviations either side, with no drift assumed. A starting point for a
    forecaster to widen or shift, not a forecast."""
    if px is None or not vol or vol <= 0:
        return None
    bars = days * ppy / 365.0
    sd = vol * math.sqrt(bars / ppy)
    return sig(px * math.exp(-1.2816 * sd), 5), sig(px * math.exp(1.2816 * sd), 5)


def share_up(series, k):
    """The share of k-bar stretches over which the series rose. None with fewer than 60 stretches."""
    if series is None or len(series) - k < 60:
        return None
    ups = sum(1 for i in range(len(series) - k) if series[i + k] > series[i])
    return ups / float(len(series) - k)


def _part_adder(parts):
    def add(pid, label, value, band, weight, text):
        parts.append({"id": pid, "label": label, "score": rnd(soft(value, band), 3), "weight": weight,
                      "value": rnd(value), "text": text})
    return add


def _above_below(v, what):
    if v is None:
        return "n/a"
    return "%.1f%% %s %s" % (abs(v) * 100, "above" if v >= 0 else "below", what)


def trend_parts(a, cash12m, ppy=252):
    """Trend readings for stocks, bonds and gold, each scored in [-1, 1].

    Two slow readings carry it: price against its 200-day average (Faber 2007) and
    12-month return in excess of T-bills (Moskowitz, Ooi and Pedersen 2012). They are
    two views of the same thing, past returns (Levine and Pedersen 2016), so adding
    more moving averages adds no information; the 50/200-day cross was dropped for
    that reason. A small 3-month reading is kept only to shorten the lag when a
    market rebounds, which is when trend rules are most wrong (Daniel and Moskowitz
    2016). Bands scale with the instrument's own volatility, so a 2% move means
    more for bonds than for stocks.
    """
    vol = a.get("vol60") or a.get("vol20") or 0.15
    parts = []
    add = _part_adder(parts)
    v = a.get("vs200")
    add("vs200", "Price vs 200-day average", v, max(0.01, 0.25 * vol), 0.45, _above_below(v, "the 200-day average"))
    r12 = a.get("ret12m")
    ex = None if r12 is None or cash12m is None else r12 - cash12m
    add("mom12", "12-month return vs T-bills", ex, max(0.02, 0.5 * vol), 0.45,
        "n/a" if ex is None else "%+.1f%% over 12 months, %s T-bills by %.1f pts" % (r12 * 100, "ahead of" if ex >= 0 else "behind", abs(ex) * 100))
    r3 = a.get("ret3m")
    add("mom3", "3-month return", r3, max(0.01, 0.25 * vol), 0.10,
        "n/a" if r3 is None else "%+.1f%% over 3 months" % (r3 * 100))
    return parts


def crypto_trend_parts(a, cash12m):
    """Trend readings for Bitcoin, weighted toward shorter horizons.

    The published evidence for crypto momentum is at days to weeks, with reversal
    beyond a month or so (Liu and Tsyvinski 2021; Liu, Tsyvinski and Wu 2022), and
    moving-average rules of 20 to 100 days have mainly reduced drawdowns (Detzel et
    al. 2021). Nothing validates a 12-month rule for crypto, so it gets a tenth.
    """
    vol = a.get("vol60") or a.get("vol20") or 0.5
    parts = []
    add = _part_adder(parts)
    for key, days, band in (("vs50", 50, 0.125), ("vs100", 100, 0.18), ("vs200", 200, 0.25)):
        v = a.get(key)
        add(key, "Price vs %d-day average" % days, v, max(0.02, band * vol), 0.20, _above_below(v, "the %d-day average" % days))
    r1 = a.get("ret1m")
    add("mom1", "1-month return", r1, max(0.02, 0.145 * vol), 0.15, "n/a" if r1 is None else "%+.1f%% over 1 month" % (r1 * 100))
    r3 = a.get("ret3m")
    add("mom3", "3-month return", r3, max(0.02, 0.25 * vol), 0.15, "n/a" if r3 is None else "%+.1f%% over 3 months" % (r3 * 100))
    r12 = a.get("ret12m")
    ex = None if r12 is None or cash12m is None else r12 - cash12m
    add("mom12", "12-month return vs T-bills", ex, max(0.05, 0.5 * vol), 0.10,
        "n/a" if ex is None else "%+.1f%% over 12 months" % (r12 * 100))
    return parts


def valuation_reading(history, value, years=40):
    """Where a valuation measure sits in its own recent past.

    history: [(iso_date, value)] oldest first. Returns (score, percentile).
    The score is 0 across the middle of the range (20th to 80th percentile of the
    trailing `years`), sliding to -1 at the 95th percentile and +1 at the 5th.
    A fixed "normal" level is avoided on purpose: the Shiller P/E has sat above its
    old average almost continuously since the 1990s, and a rule tied to that average
    amounts to a permanent underweight (Asness, Ilmanen and Maloney 2017).
    """
    if not history or value is None:
        return None, None
    last = history[-1][0]
    cutoff = "%04d%s" % (int(last[:4]) - years, last[4:])
    window = [v for d, v in history if d >= cutoff]
    if len(window) < 60:
        return None, None
    pr = percentile_rank(window, value)
    if pr >= 80:
        score = -clamp((pr - 80) / 15.0, 0, 1)
    elif pr <= 20:
        score = clamp((20 - pr) / 15.0, 0, 1)
    else:
        score = 0.0
    return score, pr


def volatility_reading(vol, norm):
    """Recent realised volatility against its long-run norm, in [-1, 0.5].

    Exposure is worth trimming when the market itself has turned violent
    (Moreira and Muir 2017; the benefit holds for the broad market after costs,
    Barroso and Detzel 2021). Calm earns only half credit: quiet markets are not
    a reason to add much risk.
    """
    if vol is None or not norm:
        return None
    ratio = vol / norm
    return min(0.5, 1 - ratio) if ratio <= 1 else -min(1.0, ratio - 1)


def rate_shock_reading(chg3m):
    """3-month change in the 10-year yield, in points: caution from +0.25, full at +1.0."""
    if chg3m is None:
        return None
    if chg3m >= 0:
        return -clamp((chg3m - 0.25) / 0.75, 0, 1)
    return clamp(-chg3m / 1.0, 0, 0.5)


def inflation_regime(cpi, cpi6m, stock_bond_corr, short_rate_chg3m):
    """Four yes/no tests of whether inflation, not growth, is driving markets.

    When it is, bonds stop cushioning stock falls and both can lose together
    (Neville et al. 2021; AQR 2023), so the defensive part of a plan should sit
    in shorter and inflation-linked bonds. Returns points 0-4, a mode, and the tests.
    """
    tests = [
        ("Inflation above 3%", None if cpi is None else cpi > 3.0,
         "n/a" if cpi is None else "12-month inflation is %.1f%%" % cpi),
        ("Inflation higher than six months ago", None if cpi is None or cpi6m is None else cpi > cpi6m,
         "n/a" if cpi is None or cpi6m is None else "%.1f%% now against %.1f%% six months ago" % (cpi, cpi6m)),
        ("Stocks and bonds falling and rising together", None if stock_bond_corr is None else stock_bond_corr > 0.2,
         "n/a" if stock_bond_corr is None else "3-month correlation of daily moves is %+.2f" % stock_bond_corr),
        ("Short-term interest rates rising", None if short_rate_chg3m is None else short_rate_chg3m >= 0.20,
         "n/a" if short_rate_chg3m is None else "3-month T-bill yield moved %+.2f pts in 3 months" % short_rate_chg3m),
    ]
    points = sum(1 for _, on, _ in tests if on)
    known = sum(1 for _, on, _ in tests if on is not None)
    mode = None if known < 2 else "short" if points >= 3 else "mixed" if points == 2 else "normal"
    return {"points": points, "known": known, "mode": mode,
            "tests": [{"label": l, "on": on, "text": t} for l, on, t in tests]}


def combine(parts):
    """Weighted mean of the parts that have a reading; None if nothing does."""
    live = [p for p in parts if p.get("score") is not None]
    w = sum(p["weight"] for p in live)
    if not live or w <= 0:
        return None
    return clamp(sum(p["score"] * p["weight"] for p in live) / w)


def bond_index(yields, duration):
    """A modelled total-return index for a bond kept at one maturity.

    yields: its yield in percent at equal monthly steps, oldest first. Each month
    earns a twelfth of the yield it started with, and gains or loses `duration`
    times the change in yield. This is the usual first-order approximation; it
    leaves out convexity and roll-down, which are small beside the yield change.
    It stands in for a fund price where no free price history exists.
    """
    idx = [100.0]
    for a, b in zip(yields, yields[1:]):
        idx.append(idx[-1] * (1 + a / 1200.0 - duration * (b - a) / 100.0))
    return idx


def monthly_trend_parts(idx, cash12m):
    """trend_parts for a monthly index, with the same three readings and weights.

    The 200-day average becomes a 10-month average, which is the rule Faber (2007)
    tested in the first place. cash12m is what cash earned over the same twelve
    months, as a fraction.
    """
    if not idx or len(idx) < 13:
        return []
    vol = realized_vol(idx, min(24, len(idx) - 1), 12) or 0.03
    parts = []
    add = _part_adder(parts)
    v = pct(idx[-1], sma(idx, 10))
    add("vs10m", "Value vs 10-month average", v, max(0.01, 0.25 * vol), 0.45, _above_below(v, "the 10-month average"))
    r12 = ret(idx, 12)
    ex = None if r12 is None or cash12m is None else r12 - cash12m
    add("mom12", "12-month return vs cash", ex, max(0.02, 0.5 * vol), 0.45,
        "n/a" if ex is None else "%+.1f%% over 12 months, %s cash by %.1f pts" % (r12 * 100, "ahead of" if ex >= 0 else "behind", abs(ex) * 100))
    r3 = ret(idx, 3)
    add("mom3", "3-month return", r3, max(0.01, 0.25 * vol), 0.10,
        "n/a" if r3 is None else "%+.1f%% over 3 months" % (r3 * 100))
    return parts


def target_inflation_reading(cpi, cpi3m, lo=1.0, hi=3.0):
    """Inflation against a central bank's target band, in [-1, 1]; good for bonds is positive.

    Half direction (a fall of half a point in three months is a full reading) and
    half level, measured from the middle of the band: zero at the middle, a full
    penalty half a point above the top of the band, a full credit as far below
    the bottom. Above the band a central bank raises rates, which is what hurts bonds.
    """
    if cpi is None:
        return None
    mid, reach = (lo + hi) / 2.0, (hi - lo) / 2.0 + 0.5
    level = -clamp((cpi - mid) / reach)
    direction = 0.0 if cpi3m is None else clamp(-(cpi - cpi3m) / 0.5)   # no history: direction counts as flat
    return clamp(0.5 * direction + 0.5 * level)


def month_name(period):
    """'2026-09' as 'September 2026'; anything else is returned unchanged."""
    try:
        return dt.date(int(period[:4]), int(period[5:7]), 1).strftime("%B %Y")
    except (TypeError, ValueError):
        return period


def parse_sdmx_csv(text):
    """SDMX CSV as {series code: [(period, value)]}, oldest first. Bad rows are skipped."""
    out = {}
    for row in csv.DictReader(io.StringIO(text)):
        try:
            out.setdefault(row["SERIES_CODE"], []).append((row["TIME_PERIOD"], float(row["OBS_VALUE"])))
        except (KeyError, TypeError, ValueError):
            continue
    for v in out.values():
        v.sort()
    return out


def align_monthly(named):
    """Keep the months every series has. named: {key: [(period, value)]}. Returns (periods, {key: values})."""
    if not named or any(not v for v in named.values()):
        return [], {}
    maps = {k: dict(v) for k, v in named.items()}
    common = sorted(set.intersection(*[set(m) for m in maps.values()]))
    return common, {k: [m[p] for p in common] for k, m in maps.items()}


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


# Israel's official statistics. Both publish open data services meant for programs.
BOI_SDMX = "https://edge.boi.gov.il/FusionEdgeServer/sdmx/v2/data/dataflow/BOI.STATISTICS"
# Bank of Israel series, monthly averages: the zero-coupon government curve in shekels
# (nominal and inflation-linked) and the inflation the bond market is pricing in.
IL_CURVE = {
    "y1": "ZC_TSB_ZND_01Y_MA", "y5": "ZC_TSB_ZND_05Y_MA", "y10": "ZC_TSB_ZND_10Y_MA",
    "real5": "ZC_TSB_ZRD_05Y_MA", "expInfl5": "EXP_EXB_ZD_5Y_MA", "expInfl1": "EXP_EXP_01Y_BI_MA",
}
IL_BOND_DURATION = 4.8   # a 5-year zero-coupon bond at about 4%; close to a broad shekel government fund
IL_CPI_TARGET = (1.0, 3.0)


def boi_rate():
    """The Bank of Israel's policy rate and the date of its next decision."""
    d = get_json("https://boi.org.il/PublicApi/GetInterest")
    return {"rate": float(d["currentInterest"]),
            "next": (d.get("nextInterestDate") or "")[:10] or None,
            "published": (d.get("lastPublishedDate") or "")[:10] or None}


def boi_usdils():
    """The Bank of Israel's representative rate for the US dollar: (shekels, timestamp)."""
    d = get_json("https://boi.org.il/PublicApi/GetExchangeRate?key=USD")
    return float(d["currentExchangeRate"]) / float(d.get("unit") or 1), (d.get("lastUpdate") or "")[:19] + "Z"


def boi_series(flow, codes, start):
    url = "%s/%s/1.0/%s?startperiod=%s&format=csv" % (BOI_SDMX, flow, "+".join(codes), start)
    return parse_sdmx_csv(http_get(url, accept="text/csv, */*", timeout=60).decode("utf-8-sig", "replace"))


def cbs_cpi(n=16):
    """Israel's general consumer price index, newest first: [(YYYY-MM, % in the month, % over 12 months)]."""
    d = get_json("https://api.cbs.gov.il/index/data/price?id=120010&format=json&download=false&last=%d" % n)
    rows = [("%04d-%02d" % (int(x["year"]), int(x["month"])), x.get("percent"), x.get("percentYear"))
            for x in d["month"][0]["date"]]
    rows = [r for r in rows if isinstance(r[2], (int, float))]
    rows.sort(reverse=True)
    if not rows:
        raise RuntimeError("no CPI rows")
    return rows


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
    # The dollar in shekels, for investors whose spending is in shekels.
    if "ILS=X" in assets:
        macro["usdils"] = rnd(assets["ILS=X"]["px"], 4)
        macro["usdils3m"] = assets["ILS=X"].get("ret3m")
        macro["usdils12m"] = assets["ILS=X"].get("ret12m")
        ils = series["ILS=X"][1]
        macro["usdils2yLow"] = rnd(min(ils), 4)
        macro["usdils2yHigh"] = rnd(max(ils), 4)

    def fetch_valuation():
        cape_hist = multpl_history("shiller-pe")
        cape = cape_hist[-1][1]
        macro["cape"] = cape
        macro["capeAsOf"] = cape_hist[-1][0]
        macro["capePct"] = rnd(percentile_rank([v for _, v in cape_hist], cape), 0)
        since = [v for d, v in cape_hist if d >= "1990-01-01"]
        macro["capePctSince1990"] = rnd(percentile_rank(since, cape), 0)
        macro["capeMedian"] = rnd(sorted(v for _, v in cape_hist)[len(cape_hist) // 2], 1)
        vs, vp = valuation_reading(cape_hist, cape, 40)
        macro["capeScore"] = rnd(vs, 3)
        macro["capePct40"] = rnd(vp, 0)
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
        macro["cpi6mAgo"] = rows[6][1]
        macro["cpi12mAgo"] = rows[12][1]
        macro["cpiTrail"] = [r[1] for r in rows[:13]][::-1]
        return True
    source("inflation", fetch_inflation, "multpl.com: US CPI inflation, year over year (BLS data)")

    if macro.get("y3m") is not None and macro.get("cpi") is not None:
        macro["realCash"] = rnd(macro["y3m"] - macro["cpi"], 2)
    if macro.get("y5y") is not None and macro.get("cpi") is not None:
        macro["realBond"] = rnd(macro["y5y"] - macro["cpi"], 2)

    # ---- stocks and bonds: together or apart? ---------------------------------
    if "VTI" in series and "IEF" in series:
        dv, _, av = series["VTI"]
        di, _, ai = series["IEF"]
        av, ai = av or series["VTI"][1], ai or series["IEF"][1]
        common = sorted(set(dv) & set(di))[-64:]
        mv, mi = dict(zip(dv, av)), dict(zip(di, ai))
        rv = [math.log(mv[common[i + 1]] / mv[common[i]]) for i in range(len(common) - 1)]
        rb_ = [math.log(mi[common[i + 1]] / mi[common[i]]) for i in range(len(common) - 1)]
        c = pearson(rv, rb_) if len(rv) >= 40 else None
        macro["stockBondCorr"] = rnd(c, 2)
    if "CL=F" in series:
        oil = series["CL=F"][1]
        macro["oil"] = rnd(oil[-1], 2)
        macro["oilVsHigh"] = rnd(pct(oil[-1], max(oil)))
    macro["inflationRegime"] = inflation_regime(macro.get("cpi"), macro.get("cpi6mAgo"),
                                                macro.get("stockBondCorr"), macro.get("y3mChg3m"))

    # ---- risk conditions ------------------------------------------------------
    regime_parts = []

    def rpart(pid, label, score, weight, text):
        regime_parts.append({"id": pid, "label": label, "score": rnd(score, 3), "weight": weight, "text": text})

    # Credit: high-yield bonds against Treasuries of similar maturity, so the reading
    # reflects fear of default rather than a move in interest rates.
    credit, base = None, ("IEI" if "IEI" in series else "IEF")
    if "HYG" in series and base in series:
        dh, _, ah = series["HYG"]
        di, _, ai = series[base]
        ah, ai = ah or series["HYG"][1], ai or series[base][1]
        common = sorted(set(dh) & set(di))
        mh, mi = dict(zip(dh, ah)), dict(zip(di, ai))
        ratio = [mh[d] / mi[d] for d in common]
        if len(ratio) > 200:
            vs = pct(ratio[-1], sma(ratio, 200))
            ch = ret(ratio, 63)
            credit = clamp(0.6 * soft(vs, 0.03) + 0.4 * soft(ch, 0.03))
            macro["creditVs200"] = rnd(vs)
            macro["credit3m"] = rnd(ch)
            rpart("credit", "Credit markets", credit, 0.50,
                  "High-yield bonds are %.1f%% %s their 200-day trend against Treasuries (%+.1f%% over 3 months)" %
                  (abs(vs) * 100, "above" if vs >= 0 else "below", ch * 100))
    if credit is None:
        rpart("credit", "Credit markets", None, 0.50, "No reading")

    vol20 = A("VTI", "vol20")
    vscore = volatility_reading(vol20, 0.16)
    rpart("volatility", "Recent stock volatility", vscore, 0.30,
          "No reading" if vol20 is None else "US stocks have swung at a %.0f%% yearly rate over the last month, against a long-run 16%%" % (vol20 * 100))

    rscore = rate_shock_reading(macro.get("y10yChg3m"))
    rpart("rates", "Interest-rate shock", rscore, 0.15,
          "No reading" if rscore is None else "10-year Treasury yield moved %+.2f pts in 3 months" % macro["y10yChg3m"])

    above = [s for s in SECTORS if (A(s, "vs200") or 0) > 0]
    have = [s for s in SECTORS if A(s, "vs200") is not None]
    if have:
        share = len(above) / len(have)
        macro["breadth"] = rnd(share, 2)
        if A("RSP", "ret3m") is not None and A("SPY", "ret3m") is not None:
            macro["equalWeightRel3m"] = rnd(A("RSP", "ret3m") - A("SPY", "ret3m"))
        rpart("breadth", "Market breadth", clamp((share - 0.5) * 2.0), 0.05,
              "%d of %d sectors are above their 200-day average" % (len(above), len(have)))
    else:
        rpart("breadth", "Market breadth", None, 0.05, "No reading")

    regime_score = combine(regime_parts)
    # Widely quoted gauges that the evidence does not support as stock signals. Shown, not scored.
    context = []
    if macro.get("vix") is not None:
        vix = macro["vix"]
        band = "calm" if vix < 17 else "normal" if vix < 21 else "elevated" if vix < 28 else "stressed"
        context.append({"label": "VIX", "text": "%.1f, %s. A high VIX marks risk, but has not predicted lower returns." % (vix, band)})
    if macro.get("curve") is not None:
        cv = macro["curve"]
        context.append({"label": "Yield curve", "text": "10-year yield is %.2f pts %s the 3-month bill. An inverted curve has preceded recessions, but it gave a false alarm from 2022 to 2024 and has not predicted stock returns." % (abs(cv), "above" if cv >= 0 else "below")})
    if macro.get("oilVsHigh") is not None:
        context.append({"label": "Oil", "text": "$%.0f a barrel, %.0f%% below its 2-year high. Most US recessions since 1945 followed an oil spike." % (macro["oil"], abs(macro["oilVsHigh"]) * 100)})
    regime = {"score": rnd(regime_score, 3), "label": label_for(regime_score), "parts": regime_parts, "context": context}

    # ---- sleeves ------------------------------------------------------------
    cash12m = A("SGOV", "ret12m")
    if cash12m is None and macro.get("y3m") is not None:
        cash12m = macro["y3m"] / 100.0
    macro["cash12m"] = rnd(cash12m)

    def trend_block(sym, ppy=252):
        a = assets.get(sym)
        if not a:
            return None, []
        parts = crypto_trend_parts(a, cash12m) if ppy == 365 else trend_parts(a, cash12m, ppy)
        return combine(parts), parts

    sleeves = {}

    def sleeve(key, parts, cap=None):
        score = combine(parts)
        note = None
        if cap is not None and score is not None and score > cap[0]:
            score, note = cap
        sleeves[key] = {"label": CORE[key]["label"], "sym": CORE[key]["sym"], "score": rnd(score, 3),
                        "stance": label_for(score), "parts": parts}
        if note:
            sleeves[key]["capNote"] = note

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

    risk_text = "Credit, volatility, interest rates and breadth together read %s" % regime["label"].lower()
    dxy_vs = macro.get("dxyVs200")
    dollar_score = None if dxy_vs is None else -soft(dxy_vs, 0.03)  # a weaker dollar helps non-US assets and gold
    dollar_text = "No reading" if dxy_vs is None else "US dollar index is %.1f%% %s its 200-day average" % (abs(dxy_vs) * 100, "above" if dxy_vs >= 0 else "below")

    # US stocks. Valuation is a slow, weak signal, so it gets a tenth and one other job:
    # when prices are in the top tenth of their 40-year range it caps how far the plan may lean in.
    us_t, us_tp = trend_block("VTI")
    cape = macro.get("cape")
    val_score, val_pct = macro.get("capeScore"), macro.get("capePct40")
    val_text = "No reading" if cape is None or val_pct is None else "Shiller P/E is %.1f, higher than %d%% of the last 40 years" % (cape, int(val_pct))
    stretched = val_pct is not None and val_pct >= 90
    sleeve("us", [
        P("trend", "Trend", us_t, 0.70, trend_text("VTI", us_t), us_tp),
        P("risk", "Risk conditions", regime_score, 0.20, risk_text),
        P("value", "Valuation", val_score, 0.10, val_text),
    ], cap=(0.5, "Held at +0.50 because prices are in the top tenth of their 40-year range") if stretched else None)

    # International stocks
    in_t, in_tp = trend_block("VXUS")
    sleeve("intl", [
        P("trend", "Trend", in_t, 0.65, trend_text("VXUS", in_t), in_tp),
        P("risk", "Risk conditions", regime_score, 0.20, risk_text),
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
        # Half direction, half level. The level penalty runs from nothing at 2.5% to full at 4%.
        infl_score = clamp(0.5 * clamp(-d3 / 0.5) - 0.5 * clamp((lvl - 2.5) / 1.5))
        infl_text = "Inflation is %.1f%% (%s), %s %.1f%% three months earlier" % (
            lvl, macro.get("cpiAsOf"), "up from" if d3 > 0 else "down from" if d3 < 0 else "unchanged from", macro["cpi3mAgo"])
    sleeve("bonds", [
        P("trend", "Trend", bo_t, 0.45, trend_text("BND", bo_t), bo_tp),
        P("carry", "Yield after inflation", carry_score, 0.30, carry_text),
        P("inflation", "Inflation level and direction", infl_score, 0.25, infl_text),
    ])

    # Gold. Its old link to real interest rates broke after 2022 (central-bank buying), so that
    # reading now counts for a tenth and trend carries most of the weight.
    go_t, go_tp = trend_block("IAU")
    rr_score, rr_text = None, "No reading"
    if macro.get("y10yChg3m") is not None:
        d_infl = (macro["cpi"] - macro["cpi3mAgo"]) if macro.get("cpi") is not None and macro.get("cpi3mAgo") is not None else 0.0
        real_chg = macro["y10yChg3m"] - d_infl
        rr_score = -soft(real_chg, 0.6)  # rising real yields raise the cost of holding gold
        rr_text = "10-year yield moved %+.2f pts in 3 months against a %+.2f pt move in inflation" % (macro["y10yChg3m"], d_infl)
    sleeve("gold", [
        P("trend", "Trend", go_t, 0.75, trend_text("IAU", go_t), go_tp),
        P("real", "Real interest rates", rr_score, 0.10, rr_text),
        P("dollar", "US dollar", dollar_score, 0.15, dollar_text),
    ])

    # Cash has no trend; its appeal is its yield after inflation.
    rc = macro.get("realCash")
    sleeves["cash"] = {"label": CORE["cash"]["label"], "sym": "SGOV", "score": None, "stance": "Anchor",
                       "parts": [P("yield", "Yield", None, 1.0,
                                   "No reading" if macro.get("y3m") is None else "3-month T-bills yield %.2f%%%s" % (
                                       macro["y3m"], "" if rc is None else ", %.1f pts %s inflation" % (abs(rc), "above" if rc >= 0 else "below")))]}

    # ---- Israel -------------------------------------------------------------
    # Official figures for an investor whose steady money is in shekels. A reading built on
    # US bonds says nothing about shekel bonds, so those get one of their own, built the
    # same way as the US one: trend, yield after inflation, and inflation itself.
    israel = {}

    def fetch_boi():
        r = boi_rate()
        israel.update({"rate": rnd(r["rate"], 2), "rateNext": r["next"], "ratePublished": r["published"]})
        try:
            fx, at = boi_usdils()
            israel["usdils"], israel["usdilsAt"] = rnd(fx, 4), at
        except Exception as e:
            log("  no representative dollar rate (%s)" % str(e)[:80])
        return True
    source("boi", fetch_boi, "Bank of Israel: policy rate, next decision date and the official dollar rate")

    def fetch_il_cpi():
        rows = cbs_cpi(16)
        israel.update({"cpi": rows[0][2], "cpiPeriod": rows[0][0], "cpiMonth": rows[0][1],
                       "cpiTarget": list(IL_CPI_TARGET), "cpiTrail": [r[2] for r in rows[:13]][::-1]})
        if len(rows) > 3:
            israel["cpi3mAgo"] = rows[3][2]
        if len(rows) > 12:
            israel["cpi12mAgo"] = rows[12][2]
        return True
    source("israelCpi", fetch_il_cpi, "Israel Central Bureau of Statistics: consumer price index")

    il_curve = {}

    def fetch_il_curve():
        got = boi_series("ZCM", sorted(IL_CURVE.values()), "%04d-01-01" % (NOW().year - 6))
        for k, code in IL_CURVE.items():
            if got.get(code):
                il_curve[k] = got[code]
        if len(il_curve.get("y5", [])) < 14:
            raise RuntimeError("5-year yield history too short")
        return True
    source("israelBonds", fetch_il_curve, "Bank of Israel: shekel government bond yields and expected inflation, monthly averages")

    if israel.get("usdils") is not None and macro.get("usdils") is None:
        macro["usdils"] = israel["usdils"]
    if il_curve.get("y5"):
        y5 = il_curve["y5"]
        y5v = [v for _, v in y5]
        israel["yieldsAsOf"] = y5[-1][0]
        for k in IL_CURVE:
            if il_curve.get(k) and il_curve[k][-1][0] == y5[-1][0]:
                israel[k] = rnd(il_curve[k][-1][1], 2)
        israel["y5Chg3m"] = rnd(y5v[-1] - y5v[-4], 2)
        israel["y5Chg12m"] = rnd(y5v[-1] - y5v[-13], 2)
        months, cols = align_monthly({k: il_curve[k] for k in ("y5", "real5") if il_curve.get(k)})
        if len(months) >= 13:
            israel["curve"] = dict({"from": months[-60:][0], "to": months[-1]},
                                   **{k: [rnd(v, 2) for v in vals[-60:]] for k, vals in cols.items()})

        idx = bond_index(y5v, IL_BOND_DURATION)
        israel["bond12m"], israel["bond3m"] = rnd(ret(idx, 12)), rnd(ret(idx, 3))
        # What cash earned over the same year: a one-year Makam bought twelve months ago paid its yield then.
        y1_then = dict(il_curve.get("y1") or []).get(y5[-13][0])
        il_cash12m = y1_then / 100.0 if y1_then is not None else (israel["rate"] / 100.0 if israel.get("rate") is not None else None)
        israel["cash12m"] = rnd(il_cash12m)
        il_tp = monthly_trend_parts(idx, il_cash12m)
        il_t = combine(il_tp)
        v10 = pct(idx[-1], sma(idx, 10))
        il_trend_text = "No reading" if v10 is None else "A 5-year shekel government bond is %.1f%% %s its 10-month average; 12-month return %s" % (
            abs(v10) * 100, "above" if v10 >= 0 else "below", "n/a" if israel["bond12m"] is None else "%+.1f%%" % (israel["bond12m"] * 100))

        il_cpi, il_real = israel.get("cpi"), israel.get("real5")
        if il_real is not None:
            il_carry = clamp((il_real - 0.5) / 1.5)
            il_carry_text = "5-year shekel government bonds yield %.2f%%, and the inflation-linked ones pay %.2f%% on top of inflation" % (y5v[-1], il_real)
        elif il_cpi is not None:
            il_carry = clamp((y5v[-1] - il_cpi - 0.5) / 1.5)
            il_carry_text = "5-year shekel government bonds yield %.2f%%, which is %.1f pts %s inflation" % (
                y5v[-1], abs(y5v[-1] - il_cpi), "above" if y5v[-1] >= il_cpi else "below")
        else:
            il_carry, il_carry_text = None, "No reading"
        il_infl = target_inflation_reading(il_cpi, israel.get("cpi3mAgo"), *IL_CPI_TARGET)
        il_infl_text = "No reading"
        if il_cpi is not None:
            was = israel.get("cpi3mAgo")
            il_infl_text = "Israeli inflation is %.1f%% (%s)%s; the Bank of Israel aims for %g to %g%%" % (
                il_cpi, month_name(israel.get("cpiPeriod")),
                "" if was is None else ", %s %.1f%% three months earlier" % ("up from" if il_cpi > was else "down from" if il_cpi < was else "unchanged from", was),
                IL_CPI_TARGET[0], IL_CPI_TARGET[1])
        il_parts = [
            P("trend", "Trend", il_t, 0.45, il_trend_text, il_tp),
            P("carry", "Yield after inflation", il_carry, 0.30, il_carry_text),
            P("inflation", "Inflation level and direction", il_infl, 0.25, il_infl_text),
        ]
        il_score = combine(il_parts)
        israel["bonds"] = {"label": "Shekel government bonds", "sym": "IL5Y", "score": rnd(il_score, 3),
                           "stance": label_for(il_score), "parts": il_parts, "asOf": y5[-1][0],
                           "note": "Trend here is worked out from the Bank of Israel's monthly average yields for a 5-year "
                                   "government bond. It models what a bond fund would have earned and is not a fund price"}

    # ---- hot names, for the one-day forecast test -----------------------------
    hot = {"stocks": [], "coins": [], "assets": {}}

    def fetch_hot():
        want = [s for s in list(HOT_STOCKS) + list(HOT_COINS) if s not in series]
        got = yahoo_spark(want)
        still = [s for s in want if s not in got]
        if still and got:
            time.sleep(3)
            got.update(yahoo_spark(still))
        for s in list(HOT_STOCKS) + list(HOT_COINS):
            ppy = 365 if s in HOT_COINS else 252
            if s in series:
                info = assets[s]
            elif s in got:
                info = analyze(got[s][0], got[s][1], None, ppy)
            else:
                continue
            row = {k: info.get(k) for k in HOT_KEEP}
            row["name"] = HOT_COINS.get(s) or HOT_STOCKS.get(s)
            row["kind"] = "crypto" if s in HOT_COINS else "stock"
            hot["assets"][s] = row
        if len(hot["assets"]) < 20:
            raise RuntimeError("only %d of the hot-name series loaded" % len(hot["assets"]))
        hot["stocks"] = hot_picks(hot["assets"], HOT_STOCKS)
        hot["coins"] = hot_picks(hot["assets"], HOT_COINS)
        return True
    source("hot", fetch_hot, "Yahoo Finance: 58 well-known shares and coins, for the one-day forecast test")

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

    # Stablecoin supply and the mood index have no reliable lead over prices in the
    # published tests, so each counts for a twentieth. The mood index is used on the
    # greed side only; "buy when others are fearful" has not held up at short horizons.
    liq_score, liq_text = None, "No reading"
    st = crypto.get("stables")
    if st and st.get("chg30") is not None:
        liq_score = clamp(0.6 * soft(st["chg30"], 0.03) + 0.4 * soft(st.get("chg90") or 0, 0.06))
        liq_text = "Stablecoin supply is $%.0fB, %+.1f%% in 30 days and %+.1f%% in 90" % (st["usd"] / 1e9, st["chg30"] * 100, (st.get("chg90") or 0) * 100)
    sent_score, sent_text = None, "No reading"
    fg = crypto.get("fng")
    if fg:
        n = fg["now"]
        sent_score = -0.6 if n >= 85 else -0.3 if n >= 75 else 0.0
        sent_text = "Fear and Greed Index is %d (%s); only extreme greed counts, as a caution" % (n, fg["label"])
    sleeve("crypto", [
        P("trend", "Bitcoin trend", btc_t, 0.65, trend_text("BTC-USD", btc_t), btc_tp),
        P("risk", "Risk conditions", regime_score, 0.25, risk_text),
        P("liquidity", "Crypto liquidity", liq_score, 0.05, liq_text),
        P("sentiment", "Crowd mood", sent_score, 0.05, sent_text),
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
        "v": 2,
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
        "israel": israel,
        "hot": hot,
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
    ta = s["assets"].get("^TA125.TA") or {}
    L.append("Israel: US dollar %s shekels (3m %s, 12m %s) | Tel Aviv 125 %s (12m %s)" % (m.get("usdils"), f(m.get("usdils3m")), f(m.get("usdils12m")), ta.get("px"), f(ta.get("ret12m"))))
    L.append("Valuation: CAPE %s (all-time pct %s, 40-year pct %s) | P/E %s | dividend yield %s" % (m.get("cape"), m.get("capePct"), m.get("capePct40"), m.get("pe"), m.get("divYield")))
    L.append("Inflation: CPI %s%% (%s), 3m ago %s%%, 6m ago %s%% | real cash %s | real 5y %s" % (m.get("cpi"), m.get("cpiAsOf"), m.get("cpi3mAgo"), m.get("cpi6mAgo"), m.get("realCash"), m.get("realBond")))
    ir = m.get("inflationRegime") or {}
    L.append("Inflation regime: %s of 4 tests (%s) | stock-bond correlation %s" % (ir.get("points"), ir.get("mode"), m.get("stockBondCorr")))
    L.append("")
    L.append("Risk regime: %s (%s)" % (s["regime"]["label"], s["regime"]["score"]))
    for p in s["regime"]["parts"]:
        L.append("   %-24s w%.2f %6s  %s" % (p["label"], p["weight"], p["score"], p["text"]))
    for c in s["regime"].get("context", []):
        L.append("   (context) %-12s %s" % (c["label"], c["text"]))
    L.append("")
    for k, sl in s["sleeves"].items():
        L.append("%-22s %-18s score %s%s" % (sl["label"], sl["stance"], sl["score"], "  [" + sl["capNote"] + "]" if sl.get("capNote") else ""))
        for p in sl["parts"]:
            L.append("   %-24s w%.2f %6s  %s" % (p["label"], p["weight"], p["score"], p["text"]))
    il = s.get("israel") or {}
    if il:
        L.append("")
        L.append("Israel (official): Bank of Israel rate %s%%, next decision %s | inflation %s%% (%s), 3m ago %s%% | dollar %s shekels" % (
            il.get("rate"), il.get("rateNext"), il.get("cpi"), il.get("cpiPeriod"), il.get("cpi3mAgo"), il.get("usdils")))
        L.append("Shekel government yields (%s averages): 1y %s  5y %s  10y %s | 5y inflation-linked %s | market-implied inflation 5y %s" % (
            il.get("yieldsAsOf"), il.get("y1"), il.get("y5"), il.get("y10"), il.get("real5"), il.get("expInfl5")))
        ib = il.get("bonds")
        if ib:
            L.append("%-22s %-18s score %s" % (ib["label"], ib["stance"], ib["score"]))
            for p in ib["parts"]:
                L.append("   %-24s w%.2f %6s  %s" % (p["label"], p["weight"], p["score"], p["text"]))
    L.append("")
    L.append("Forecast guide (the naive rule and a typical 80% range; see forecasts.py):")
    for k in FORECAST_ASSETS:
        a = s["assets"].get(k)
        if not a:
            continue
        vols = [v for v in (a.get("vol20"), a.get("vol60")) if v]
        vol = sum(vols) / len(vols) if vols else None
        ppy = 365 if k.endswith("-USD") else 252
        r7, r30 = typical_range(a["px"], vol, 7, ppy), typical_range(a["px"], vol, 30, ppy)
        L.append("   %-10s %-22s price %-9s rose in %s of weeks, %s of months | 1w %s 1m %s vs200d %s | typical range 1w %s, 1m %s" % (
            k, a["name"][:22], a["px"],
            "n/a" if a.get("up1w") is None else "%.0f%%" % (a["up1w"] * 100), "n/a" if a.get("up1m") is None else "%.0f%%" % (a["up1m"] * 100),
            f(a.get("ret1w")), f(a.get("ret1m")), f(a.get("vs200")),
            "n/a" if not r7 else "%s to %s" % r7, "n/a" if not r30 else "%s to %s" % r30))
    hot = s.get("hot") or {}
    if hot.get("stocks") or hot.get("coins"):
        L.append("")
        L.append("Hot names: the five shares and five coins with the best 12 months (one-day forecasts; see forecasts.py):")
        for k in (hot.get("stocks") or []) + (hot.get("coins") or []):
            a = hot["assets"][k]
            r1 = typical_range(a["px"], a.get("vol20"), 1, 365 if a.get("kind") == "crypto" else 252)
            L.append("   %-9s %-14s price %-9s 12m %s | rose on %s of days | today %s 1w %s 1m %s vs50d %s | typical range tomorrow %s" % (
                k, (a.get("name") or "")[:14], a["px"], f(a.get("ret12m")),
                "n/a" if a.get("up1d") is None else "%.0f%%" % (a["up1d"] * 100),
                f(a.get("chg1d")), f(a.get("ret1w")), f(a.get("ret1m")), f(a.get("vs50")), "n/a" if not r1 else "%s to %s" % r1))
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
