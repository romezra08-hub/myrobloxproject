#!/usr/bin/env python3
"""Keep the record of forecasts honest.

The forecaster (Claude, in the daily refresh) supplies only a probability, a range and a
reason. Everything that decides whether a forecast was right is done here, mechanically,
from the prices in the snapshot: the starting price, the due date, the outcome and the score.
The forecaster never grades itself.

    python3 forecasts.py resolve --snapshot snapshot.json --in old.json --out resolved.json
    python3 forecasts.py feedback --in resolved.json
    python3 forecasts.py combine --new lead.json second.json third.json --out new.json
    python3 forecasts.py add --snapshot snapshot.json --in resolved.json --new new.json --out forecasts.json

`feedback` prints the forecaster's own record in totals, for it to read before forecasting. Once
60 calls have been scored, `add` also works out how far the forecaster's departures from the
naive rule have deserved to be believed and stores each new call with that correction applied.

`--in` may name a file that does not exist yet; the record then starts empty.

A forecast says: "the chance that this asset's price is higher after N days is p, and I am
80% sure it will lie between low and high". Five markets are forecast a week and a month
ahead. The day's "hot names" (the shares and coins with the best twelve months, listed in the
snapshot) are forecast one day ahead: the very short test the owner asked for. Up to three
other well-known names a day may also get a one-day call when something has just happened to
them, such as a chief executive leaving or an exchange being hacked. Any call may carry a "news"
line naming the item it rests on, and those calls are scored as a group of their own, so the
record shows whether news of that kind helps. It is scored when the first refresh on or after
its due date runs, against the price in that refresh. A call due on a weekend is therefore
scored on the Monday.
"""
import argparse
import datetime as dt
import json
import math
import os
import sys

ASSETS = {            # what may be forecast: snapshot key -> name shown on the page
    "SPY": "US stocks (SPY fund)",
    "^TA125.TA": "Tel Aviv 125",
    "BTC-USD": "Bitcoin",
    "IAU": "Gold (IAU fund)",
    "ILS=X": "US dollar in shekels",
}
HORIZONS = (7, 30, 90)    # days, for the five markets above
HOT_HORIZON = 1       # days, for the snapshot's hot names
NEWS_CALLS_A_DAY = 3  # one-day calls allowed on other well-known names, each resting on a named news item
P_MIN, P_MAX = 0.05, 0.95
KEEP_CLOSED = 400
LEARN_MIN = 40        # scored calls needed before the record is allowed to correct new ones
PRIOR_CALLS = 60      # the record starts from "no skill": this many calls' worth of doubt is mixed in
GRACE = dt.timedelta(hours=6)   # the refresh a week later may run a minute earlier than the one that made the call
WHY_MAX = 320


def parse_time(s):
    return dt.datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc)


def empty():
    return {"v": 1, "updatedAt": None, "open": [], "closed": [], "trust": None}


def load(path):
    if not path or not os.path.exists(path):
        return empty()
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    if isinstance(d, dict) and "open" not in d and isinstance(d.get("data"), dict):
        d = d["data"]                 # some exports wrap the document
    if not isinstance(d, dict):
        return empty()
    out = empty()
    out["open"] = [x for x in d.get("open", []) if isinstance(x, dict)]
    out["closed"] = [x for x in d.get("closed", []) if isinstance(x, dict)]
    out["updatedAt"] = d.get("updatedAt")
    out["trust"] = d.get("trust") if isinstance(d.get("trust"), dict) else None
    return out


def info_of(snapshot, asset):
    """An asset's figures: from the main table, or from the wider hot-names table."""
    a = (snapshot.get("assets") or {}).get(asset)
    if not a:
        a = ((snapshot.get("hot") or {}).get("assets") or {}).get(asset)
    return a or {}


def hot_info(snapshot, asset):
    return ((snapshot.get("hot") or {}).get("assets") or {}).get(asset) or {}


def hot_names(snapshot):
    hot = snapshot.get("hot") or {}
    return [s for s in (hot.get("stocks") or []) + (hot.get("coins") or []) if isinstance(s, str)]


def price_of(snapshot, asset):
    px = info_of(snapshot, asset).get("px")
    return float(px) if isinstance(px, (int, float)) and not isinstance(px, bool) and px > 0 else None


def base_rate(snapshot, asset, horizon):
    """How often this asset rose over a stretch this long in the recent past: the naive forecast."""
    v = info_of(snapshot, asset).get("up1d" if horizon <= 1 else "up1w" if horizon <= 7 else "up1m" if horizon <= 30 else "up3m")
    return round(float(v), 3) if isinstance(v, (int, float)) and 0 <= v <= 1 else None


def resolve(record, snapshot):
    """Close every open forecast whose due date has passed, using the snapshot's prices."""
    now = parse_time(snapshot["generatedAt"])
    still, closed = [], list(record["closed"])
    for f in record["open"]:
        due = parse_time(f["dueAt"])
        px = price_of(snapshot, f["asset"])
        if now < due - GRACE or px is None:
            still.append(f)          # not due yet, or no price today: try again next time
            continue
        up = px > f["startPx"]
        g = dict(f)
        g.update({
            "endPx": px, "resolvedAt": snapshot["generatedAt"], "up": up,
            "change": round(px / f["startPx"] - 1, 5),
            "brier": round((f["pUp"] - (1.0 if up else 0.0)) ** 2, 5),
            "inRange": None if f.get("low") is None or f.get("high") is None else bool(f["low"] <= px <= f["high"]),
            "late": (now - due).total_seconds() > 3 * 86400,
        })
        if f.get("base") is not None:
            g["baseBrier"] = round((f["base"] - (1.0 if up else 0.0)) ** 2, 5)
        if f.get("pAdj") is not None:
            g["adjBrier"] = round((f["pAdj"] - (1.0 if up else 0.0)) ** 2, 5)
        closed.append(g)
    closed.sort(key=lambda x: x.get("resolvedAt") or "")
    return {"v": 1, "updatedAt": snapshot["generatedAt"], "open": still, "closed": closed[-KEEP_CLOSED:],
            "trust": record.get("trust")}


def clean_new(item, snapshot):
    """Validate one new forecast and fill in everything the forecaster must not choose. Returns (forecast, problem)."""
    if not isinstance(item, dict):
        return None, "not an object"
    asset, horizon = item.get("asset"), item.get("horizonDays")
    if isinstance(horizon, bool) or not isinstance(horizon, int):
        return None, "%r: horizonDays must be a whole number" % (asset,)
    news = " ".join(str(item.get("news") or "").split())[:200]
    if horizon == HOT_HORIZON:
        if asset not in hot_names(snapshot) and not (news and hot_info(snapshot, asset)):
            return None, "%r: a one-day forecast needs one of today's hot names, or a well-known name with a news item" % (asset,)
    elif asset not in ASSETS:
        return None, "unknown asset %r" % (asset,)
    elif horizon not in HORIZONS:
        return None, "%s: horizon must be one of %s" % (asset, list(HORIZONS))
    p = item.get("pUp")
    if not isinstance(p, (int, float)) or isinstance(p, bool) or not (0 <= p <= 1):
        return None, "%s: pUp must be a number from 0 to 1" % asset
    px = price_of(snapshot, asset)
    if px is None:
        return None, "%s: no price in the snapshot" % asset
    low, high = item.get("low"), item.get("high")
    ok_range = all(isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 for v in (low, high)) and low < high
    if not ok_range or not (low <= px * 1.5 and high >= px / 1.5):
        low = high = None                       # a range that is missing or nowhere near the price is dropped, not guessed
    own = script_range(snapshot, asset, horizon)
    if own:
        low = min(low, own[0]) if low is not None else own[0]
        high = max(high, own[1]) if high is not None else own[1]
        digits = 4 if px < 10 else 2
        low, high = round(low, digits), round(high, digits)
    runs = item.get("runs")
    made = snapshot["generatedAt"]
    due = (parse_time(made) + dt.timedelta(days=horizon)).strftime("%Y-%m-%dT%H:%M:%SZ")
    why = " ".join(str(item.get("why") or "").split())[:WHY_MAX]
    return {
        "id": "%s:%d:%s" % (asset, horizon, made[:10]),
        "asset": asset, "name": ASSETS.get(asset) if horizon != HOT_HORIZON else (str(hot_info(snapshot, asset).get("name") or asset)[:40]),
        "kind": hot_info(snapshot, asset).get("kind") if horizon == HOT_HORIZON else None,
        "horizonDays": horizon,
        "madeAt": made, "dueAt": due, "startPx": px,
        "pUp": round(min(P_MAX, max(P_MIN, float(p))), 3),     # never certain
        "low": low, "high": high, "base": base_rate(snapshot, asset, horizon), "why": why,
        "news": news or None, "onNews": bool(news),
        "runs": runs if isinstance(runs, int) and not isinstance(runs, bool) and 1 <= runs <= 9 else 1,
        "extra": horizon == HOT_HORIZON and asset not in hot_names(snapshot),   # called only because of the news
    }, None


def trust(closed):
    """How far the forecaster's departures from the naive rule have deserved to be believed.

    Each call is the usual figure plus a departure. This finds the one multiple k of that
    departure which would have scored best on the calls already settled, then pulls it toward
    zero as if PRIOR_CALLS further calls had shown no skill at all: a forecaster is assumed to
    have no edge until the record says otherwise, and a short lucky run cannot earn much trust.
    k is held between 0 and 1. It is never above 1: studies of combining forecasts find that
    stretching calls further from the usual figure only helps a forecaster who has shown skill
    and holds information the others lack (Baron and others 2014), and correlated runs of one
    model with no record of skill are the opposite case.
    Returns (k, how many calls it rests on); k is None on fewer than LEARN_MIN calls.
    """
    rows = [(f["pUp"] - f["base"], (1.0 if f["up"] else 0.0) - f["base"]) for f in closed
            if isinstance(f.get("base"), (int, float)) and isinstance(f.get("pUp"), (int, float)) and isinstance(f.get("up"), bool)]
    moved = sum(d * d for d, _ in rows)
    if len(rows) < LEARN_MIN or moved <= 1e-9:
        return None, len(rows)
    k = sum(d * e for d, e in rows) / moved
    k *= len(rows) / float(len(rows) + PRIOR_CALLS)
    return round(min(1.0, max(0.0, k)), 3), len(rows)


def script_range(snapshot, asset, horizon):
    """An 80% range worked out from the asset's own past moves, scaled to how hard it is swinging
    now. Language models give ranges that are too narrow, so the forecaster may widen this one
    but never narrow it. Returns (low, high) or None."""
    a, px = info_of(snapshot, asset), price_of(snapshot, asset)
    if px is None:
        return None
    vols = [v for v in (a.get("vol20"), a.get("vol60")) if isinstance(v, (int, float)) and v > 0]
    vol = sum(vols) / len(vols) if vols else None
    band = (a.get("band") or {}).get(str(horizon))
    if isinstance(band, list) and len(band) == 2 and band[0] < 0 < band[1]:
        whole = a.get("volAll")
        scale = min(1.8, max(0.6, vol / whole)) if vol and isinstance(whole, (int, float)) and whole > 0 else 1.0
        return px * math.exp(band[0] * scale), px * math.exp(band[1] * scale)
    if vol:
        sd = vol * math.sqrt(horizon / 365.0)
        return px * math.exp(-1.2816 * sd), px * math.exp(1.2816 * sd)
    return None


def combine(sets):
    """Average several independent sets of forecasts into one.

    Averaging removes the part of a forecaster's error that changes from run to run. The first
    set is the lead: it decides which calls are made and supplies the words. Each probability
    becomes the mean of what the sets said, leaving out the highest and lowest when there are
    four or more; each range becomes the widest any set gave.
    """
    sets = [s for s in sets if isinstance(s, list)]
    if not sets:
        return []
    def key(x):
        return (x.get("asset"), x.get("horizonDays")) if isinstance(x, dict) else None
    out = []
    for item in sets[0]:
        if not isinstance(item, dict):
            continue
        same = [x for s in sets for x in s if key(x) == key(item)]
        ps = sorted(x["pUp"] for x in same if isinstance(x.get("pUp"), (int, float)) and not isinstance(x.get("pUp"), bool) and 0 <= x["pUp"] <= 1)
        if not ps:
            continue
        if len(ps) >= 4:
            ps = ps[1:-1]
        merged = dict(item)
        merged["pUp"] = round(sum(ps) / len(ps), 3)
        lows = [x["low"] for x in same if isinstance(x.get("low"), (int, float)) and x["low"] > 0]
        highs = [x["high"] for x in same if isinstance(x.get("high"), (int, float)) and x["high"] > 0]
        if lows and highs:
            merged["low"], merged["high"] = min(lows), max(highs)
        merged["runs"] = len(same)
        out.append(merged)
    return out


def add(record, new_items, snapshot):
    """Append new forecasts. One per asset, horizon and day: a second one the same day is refused, not swapped in.
    Once enough calls have been scored, each new one also carries pAdj: the call after the record's correction."""
    have = {f["id"] for f in record["open"]} | {f["id"] for f in record["closed"]}
    k, n = trust(record["closed"])
    out, problems = list(record["open"]), []
    day = snapshot["generatedAt"][:10]
    extras = sum(1 for f in record["open"] + record["closed"] if f.get("extra") and (f.get("madeAt") or "")[:10] == day)
    for item in (new_items if isinstance(new_items, list) else []):
        f, problem = clean_new(item, snapshot)
        if problem:
            problems.append(problem)
        elif f["id"] in have:
            problems.append("%s: already forecast today" % f["id"])
        elif f["extra"] and extras >= NEWS_CALLS_A_DAY:
            problems.append("%s: only %d news calls a day" % (f["id"], NEWS_CALLS_A_DAY))
        else:
            extras += 1 if f["extra"] else 0
            if k is not None and f.get("base") is not None:
                f["pAdj"] = round(min(P_MAX, max(P_MIN, f["base"] + k * (f["pUp"] - f["base"]))), 3)
            out.append(f)
            have.add(f["id"])
    out.sort(key=lambda x: (x["dueAt"], x["asset"]))
    return {"v": 1, "updatedAt": snapshot["generatedAt"], "open": out, "closed": record["closed"],
            "trust": None if k is None else {"k": k, "n": n}}, problems


def feedback(record):
    """What the forecaster is told about its own record before it forecasts again: totals only,
    never an individual call, so that it learns its habits without anchoring on yesterday."""
    c = [f for f in record["closed"] if isinstance(f.get("base"), (int, float)) and isinstance(f.get("up"), bool)]
    if len(c) < 20:
        return "Your record so far: %d calls scored, too few to say anything about. Forecast as instructed." % len(c)
    L = ["Your record so far (%d calls scored). Read it, then correct for it." % len(c)]
    def line(label, rows):
        if len(rows) < 8:
            return
        said = sum(f["pUp"] for f in rows) / len(rows)
        usual = sum(f["base"] for f in rows) / len(rows)
        came = sum(1 for f in rows if f["up"]) / float(len(rows))
        mine = sum((f["pUp"] - (1.0 if f["up"] else 0.0)) ** 2 for f in rows) / len(rows)
        naive = sum((f["base"] - (1.0 if f["up"] else 0.0)) ** 2 for f in rows) / len(rows)
        L.append("  %-34s %3d calls | you said %2.0f%% on average, the usual figure was %2.0f%%, it rose %2.0f%% of the time | your score %.3f, naive %.3f (%s)" % (
            label, len(rows), said * 100, usual * 100, came * 100, mine, naive, "you were better" if mine < naive - 0.002 else "you were worse" if mine > naive + 0.002 else "no difference"))
    for h in sorted({f["horizonDays"] for f in c}):
        line("%d-day calls" % h, [f for f in c if f["horizonDays"] == h])
    line("calls resting on a named news item", [f for f in c if f.get("onNews")])
    line("calls with no named news item", [f for f in c if not f.get("onNews")])
    line("when you said MORE likely than usual", [f for f in c if f["pUp"] > f["base"] + 0.005])
    line("when you said LESS likely than usual", [f for f in c if f["pUp"] < f["base"] - 0.005])
    line("coins", [f for f in c if f.get("kind") == "crypto" or f["asset"].endswith("-USD")])
    line("shares and other markets", [f for f in c if not (f.get("kind") == "crypto" or f["asset"].endswith("-USD"))])
    L.append("  What you said against what happened:")
    for lo, hi, label in ((0.0, 0.45, "under 45%"), (0.45, 0.50, "45% to 50%"), (0.50, 0.55, "50% to 55%"), (0.55, 1.01, "55% or more")):
        rows = [f for f in c if lo <= f["pUp"] < hi]
        if rows:
            L.append("    said %-11s %3d calls | on average you said %2.0f%% and it rose %2.0f%% of the time" % (
                label, len(rows), 100 * sum(f["pUp"] for f in rows) / len(rows), 100 * sum(1 for f in rows if f["up"]) / float(len(rows))))
    ranged = [f for f in c if isinstance(f.get("inRange"), bool)]
    if len(ranged) >= 8:
        share = sum(1 for f in ranged if f["inRange"]) / float(len(ranged))
        L.append("  Your 80%% ranges held the price %2.0f%% of the time: %s." % (
            share * 100, "about right" if 0.72 <= share <= 0.88 else "too narrow, widen them" if share < 0.72 else "too wide, tighten them"))
    k, n = trust(record["closed"])
    if k is not None:
        L.append("  On this record, the best-scoring use of your calls would have been to take %.0f%% of each departure from the usual figure. "
                 "The page now applies that correction. %s" % (k * 100, "Your departures have added nothing so far: make them only for news you can name." if k < 0.25
                                                             else "Your departures have been too large: make smaller ones." if k < 0.8 else "Your departures have been about the right size."))
    return "\n".join(L)


def summary(record):
    c = record["closed"]
    L = ["Forecast record: %d open, %d scored" % (len(record["open"]), len(c))]
    if c:
        hits = sum(1 for f in c if (f["pUp"] > 0.5) == f["up"] and f["pUp"] != 0.5)
        calls = sum(1 for f in c if f["pUp"] != 0.5)
        brier = sum(f["brier"] for f in c) / len(c)
        based = [f for f in c if f.get("baseBrier") is not None]
        L.append("  right way round %d of %d | Brier %.3f (coin flip 0.250%s)" % (
            hits, calls, brier, "" if not based else ", naive base rate %.3f" % (sum(f["baseBrier"] for f in based) / len(based))))
        for h in sorted({f["horizonDays"] for f in c}):
            hs = [f for f in c if f["horizonDays"] == h and f["pUp"] != 0.5]
            if hs:
                L.append("  %2d-day calls: right way round %d of %d" % (h, sum(1 for f in hs if (f["pUp"] > 0.5) == f["up"]), len(hs)))
        for f in c[-8:]:
            L.append("  %-22s %2dd made %s  said %2.0f%% up  %s %+.1f%%" % (
                f["name"][:22], f["horizonDays"], f["madeAt"][:10], f["pUp"] * 100, "rose" if f["up"] else "fell", f["change"] * 100))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Resolve and extend the Market Compass forecast record")
    ap.add_argument("mode", choices=("resolve", "add", "feedback", "combine"))
    ap.add_argument("--snapshot")
    ap.add_argument("--in", dest="src", help="the record so far (may not exist yet)")
    ap.add_argument("--new", nargs="*", help="add: a JSON list of new forecasts. combine: several such files, the lead first")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    if args.mode == "feedback":
        print(feedback(load(args.src)))
        return 0
    if args.mode == "combine":
        sets = []
        for path in args.new or []:
            try:
                with open(path, encoding="utf-8") as f:
                    sets.append(json.load(f))
            except (OSError, ValueError) as e:        # a set that failed to arrive is left out, not fatal
                print("  skipped %s: %s" % (path, str(e)[:80]), file=sys.stderr)
        merged = combine(sets)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=1)
        print("Combined %d set(s) into %d forecasts" % (len(sets), len(merged)))
        return 0
    if not args.snapshot or not args.out:
        ap.error("resolve and add need --snapshot and --out")
    with open(args.snapshot, encoding="utf-8") as f:
        snapshot = json.load(f)
    record = load(args.src)
    problems = []
    if args.mode == "resolve":
        record = resolve(record, snapshot)
    else:
        with open((args.new or [None])[0], encoding="utf-8") as f:
            record, problems = add(record, json.load(f), snapshot)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(record, f, separators=(",", ":"))
    print(summary(record))
    for p in problems:
        print("  refused: " + p, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
