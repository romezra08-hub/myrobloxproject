#!/usr/bin/env python3
"""Keep the record of forecasts honest.

The forecaster (Claude, in the daily refresh) supplies only a probability, a range and a
reason. Everything that decides whether a forecast was right is done here, mechanically,
from the prices in the snapshot: the starting price, the due date, the outcome and the score.
The forecaster never grades itself.

    python3 forecasts.py resolve --snapshot snapshot.json --in old.json --out resolved.json
    python3 forecasts.py feedback --in resolved.json
    python3 forecasts.py add --snapshot snapshot.json --in resolved.json --new new.json --out forecasts.json

`feedback` prints the forecaster's own record in totals, for it to read before forecasting. Once
60 calls have been scored, `add` also works out how far the forecaster's departures from the
naive rule have deserved to be believed and stores each new call with that correction applied.

`--in` may name a file that does not exist yet; the record then starts empty.

A forecast says: "the chance that this asset's price is higher after N days is p, and I am
80% sure it will lie between low and high". Five markets are forecast a week and a month
ahead. The day's "hot names" (the shares and coins with the best twelve months, listed in the
snapshot) are forecast one day ahead: the very short test the owner asked for. It is scored when the first refresh on or after
its due date runs, against the price in that refresh. A call due on a weekend is therefore
scored on the Monday.
"""
import argparse
import datetime as dt
import json
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
P_MIN, P_MAX = 0.05, 0.95
KEEP_CLOSED = 400
LEARN_MIN = 60        # scored calls needed before the record is allowed to correct new ones
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
    if horizon == HOT_HORIZON:
        if asset not in hot_names(snapshot):
            return None, "%r: one-day forecasts are only for today's hot names" % (asset,)
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
    }, None


def trust(closed):
    """How far the forecaster's departures from the naive rule have deserved to be believed.

    Each call is the usual figure plus a departure. This finds the one multiple k of that
    departure which would have scored best on the calls already settled: 1 means take the
    calls as given, 0 means the departures were worth nothing and the usual figure alone
    did better, and a value between shrinks them. It is held between 0 and 1.5 and is not
    estimated at all on fewer than LEARN_MIN calls, when it would mostly measure luck.
    Returns (k, how many calls it rests on).
    """
    rows = [(f["pUp"] - f["base"], (1.0 if f["up"] else 0.0) - f["base"]) for f in closed
            if isinstance(f.get("base"), (int, float)) and isinstance(f.get("pUp"), (int, float)) and isinstance(f.get("up"), bool)]
    moved = sum(d * d for d, _ in rows)
    if len(rows) < LEARN_MIN or moved <= 1e-9:
        return None, len(rows)
    k = sum(d * e for d, e in rows) / moved
    return round(min(1.5, max(0.0, k)), 3), len(rows)


def add(record, new_items, snapshot):
    """Append new forecasts. One per asset, horizon and day: a second one the same day is refused, not swapped in.
    Once enough calls have been scored, each new one also carries pAdj: the call after the record's correction."""
    have = {f["id"] for f in record["open"]} | {f["id"] for f in record["closed"]}
    k, n = trust(record["closed"])
    out, problems = list(record["open"]), []
    for item in (new_items if isinstance(new_items, list) else []):
        f, problem = clean_new(item, snapshot)
        if problem:
            problems.append(problem)
        elif f["id"] in have:
            problems.append("%s: already forecast today" % f["id"])
        else:
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
    line("when you said MORE likely than usual", [f for f in c if f["pUp"] > f["base"] + 0.005])
    line("when you said LESS likely than usual", [f for f in c if f["pUp"] < f["base"] - 0.005])
    line("coins", [f for f in c if f.get("kind") == "crypto" or f["asset"].endswith("-USD")])
    line("shares and other markets", [f for f in c if not (f.get("kind") == "crypto" or f["asset"].endswith("-USD"))])
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
    ap.add_argument("mode", choices=("resolve", "add", "feedback"))
    ap.add_argument("--snapshot")
    ap.add_argument("--in", dest="src", help="the record so far (may not exist yet)")
    ap.add_argument("--new", help="add: a JSON list of new forecasts")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    if args.mode == "feedback":
        print(feedback(load(args.src)))
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
        with open(args.new, encoding="utf-8") as f:
            record, problems = add(record, json.load(f), snapshot)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(record, f, separators=(",", ":"))
    print(summary(record))
    for p in problems:
        print("  refused: " + p, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
