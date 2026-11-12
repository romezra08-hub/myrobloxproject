#!/usr/bin/env python3
"""A blind test of short-term forecasting on the hottest stocks and coins.

The forecaster is shown anonymous cases: an asset's recent price behaviour up to one day,
with the name and the date removed. It gives the chance that the price is higher one bar
later and five bars later (a bar is a trading day for stocks and a calendar day for crypto).
Only then are the outcomes looked up and scored.

Why it is a fair test of the model: every case is dated after the model's training ended, so
it cannot remember what happened. The assets are the best performers of the previous twelve
months as measured at the START of the test window, which is what "pick the hot names"
means in practice; choosing them with hindsight would flatter any forecaster.

    python3 blind_test.py fetch  --cache raw.json
    python3 blind_test.py cases  --cache raw.json --out cases.json --key key.json
    python3 blind_test.py score  --cache raw.json --key key.json --pred a.json b.json --out blind_results.json

`cases.json` holds no outcomes. Cases for one asset are at least ten bars apart and show only
the last five daily moves, so no case reveals the answer to another.
"""
import argparse
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pipeline"))
import refresh as r  # noqa: E402

STOCKS, COINS = list(r.HOT_STOCKS), list(r.HOT_COINS)   # the same well-known names the daily test draws on
TEST_FROM = "2026-08-01"     # after the model's training ended
N_STOCKS, N_COINS = 10, 8
SPACING, SHOWN, AHEAD = 10, 5, 5


def fetch(cache):
    got = r.yahoo_spark(STOCKS + COINS, rng="2y")
    missing = [s for s in STOCKS + COINS if s not in got]
    if missing:
        got.update(r.yahoo_spark(missing, rng="2y"))
    raw = {s: [d, c] for s, (d, c, _) in got.items()}
    with open(cache, "w") as f:
        json.dump(raw, f)
    print("%d of %d series; missing: %s" % (len(raw), len(STOCKS + COINS), [s for s in STOCKS + COINS if s not in raw]))


def load(cache):
    with open(cache) as f:
        return json.load(f)


def start_index(dates):
    for i, d in enumerate(dates):
        if d >= TEST_FROM:
            return i
    return None


def hottest(raw):
    """The best performers over the twelve months before the test window opened."""
    def ranked(symbols, bars, n):
        out = []
        for s in symbols:
            if s not in raw:
                continue
            d, c = raw[s]
            i = start_index(d)
            if i is None or i - 1 - bars < 0 or len(d) - i < SPACING + AHEAD:
                continue
            out.append((c[i - 1] / c[i - 1 - bars] - 1, s))
        out.sort(reverse=True)
        return out[:n]
    return ranked(STOCKS, 252, N_STOCKS), ranked(COINS, 365, N_COINS)


def features(c, i, ppy):
    """What the forecaster sees for a case whose last known bar is index i."""
    seg = c[: i + 1]
    k1m, k3m = round(ppy / 12), round(ppy / 4)
    pc = lambda x: None if x is None else round(x * 100, 1)
    hist = seg[-(ppy + 1):]
    return {
        "last5": [round((seg[-j] / seg[-j - 1] - 1) * 100, 1) for j in range(SHOWN, 0, -1)],
        "m1": pc(r.ret(seg, k1m)), "m3": pc(r.ret(seg, k3m)), "m12": pc(r.ret(seg, ppy)),
        "vs50": pc(r.pct(seg[-1], r.sma(seg, 50))), "vs200": pc(r.pct(seg[-1], r.sma(seg, 200))),
        "vol": pc(r.realized_vol(seg, 20, ppy)),
        "base1": pc(r.share_up(hist, 1)), "base5": pc(r.share_up(hist, 5)),
    }


def make_cases(raw, seed=20261112):
    rng = random.Random(seed)
    stocks, coins = hottest(raw)
    cases, key = [], {}
    for kind, picks, ppy in (("stock", stocks, 252), ("crypto", coins, 365)):
        for _, sym in picks:
            d, c = raw[sym]
            i = start_index(d) + rng.randrange(SPACING)
            while i + AHEAD < len(c):
                cid = "c%04d" % rng.randrange(10000)
                while cid in key:
                    cid = "c%04d" % rng.randrange(10000)
                key[cid] = {"sym": sym, "date": d[i], "kind": kind}
                cases.append(dict({"id": cid, "kind": kind}, **features(c, i, ppy)))
                i += SPACING
    rng.shuffle(cases)
    return cases, key, {"stocks": [(s, round(x, 3)) for x, s in stocks], "coins": [(s, round(x, 3)) for x, s in coins]}


def as_table(cases):
    L = ["id | kind | last 5 daily moves %, oldest first | 1 month % | 3 months % | 12 months % | vs 50-bar avg % | vs 200-bar avg % | "
         "yearly swing % | usual chance up next bar % | usual chance up over 5 bars %"]
    for c in cases:
        L.append(" | ".join(str(x) for x in (c["id"], c["kind"], " ".join("%+.1f" % v for v in c["last5"]), c["m1"], c["m3"], c["m12"],
                                             c["vs50"], c["vs200"], c["vol"], c["base1"], c["base5"])))
    return "\n".join(L)


def score(raw, key, preds, cases=None):
    by_id = {}
    for p in preds:
        if isinstance(p, dict) and p.get("id") in key and p["id"] not in by_id:
            by_id[p["id"]] = p
    feat = {c["id"]: c for c in (cases or [])}
    rows = []
    for cid, k in key.items():
        d, c = raw[k["sym"]]
        i = d.index(k["date"])
        for h, field, base in ((1, "p1", "base1"), (AHEAD, "p5", "base5")):
            p = by_id.get(cid, {}).get(field)
            if not isinstance(p, (int, float)) or isinstance(p, bool) or not (0 <= p <= 1):
                continue
            ret = c[i + h] / c[i] - 1
            b = (feat.get(cid) or {}).get(base)
            rows.append({"id": cid, "kind": k["kind"], "h": h, "p": min(0.95, max(0.05, p)), "up": ret > 0, "ret": ret,
                         "base": None if b is None else b / 100.0,
                         "mom": (feat.get(cid) or {}).get("last5")})
    def stats(rs):
        n = len(rs)
        if not n:
            return None
        calls = [x for x in rs if x["p"] != 0.5]
        hits = sum(1 for x in calls if (x["p"] > 0.5) == x["up"])
        brier = sum((x["p"] - (1 if x["up"] else 0)) ** 2 for x in rs) / n
        based = [x for x in rs if x["base"] is not None]
        bb = sum((x["base"] - (1 if x["up"] else 0)) ** 2 for x in based) / len(based) if based else None
        mine = sum((x["p"] - (1 if x["up"] else 0)) ** 2 for x in based) / len(based) if based else None
        # did the calls sort good days from bad? the average move after a call above the usual chance, and below it
        hi = [x["ret"] for x in based if x["p"] > x["base"]]
        lo = [x["ret"] for x in based if x["p"] < x["base"]]
        # a rule a child could follow: say "up" if the last five days were up overall
        mom = [x for x in rs if x["mom"]]
        mom_hits = sum(1 for x in mom if (sum(x["mom"]) > 0) == x["up"])
        rnd = lambda v, k=4: None if v is None else round(v, k)
        return {"n": n, "calls": len(calls), "hits": hits, "hitRate": rnd(hits / len(calls)) if calls else None,
                "upRate": rnd(sum(1 for x in rs if x["up"]) / n), "brier": rnd(brier), "baseBrier": rnd(bb),
                "skill": rnd(1 - mine / bb) if bb else None,
                "avgAfterHigh": rnd(sum(hi) / len(hi)) if hi else None, "nHigh": len(hi),
                "avgAfterLow": rnd(sum(lo) / len(lo)) if lo else None, "nLow": len(lo),
                "avgAll": rnd(sum(x["ret"] for x in rs) / n),
                "momentumHitRate": rnd(mom_hits / len(mom)) if mom else None,
                "avgP": rnd(sum(x["p"] for x in rs) / n)}
    out = {"cases": len(key), "answered": len(by_id), "from": TEST_FROM,
           "to": max(k["date"] for k in key.values()), "all": {}, "stock": {}, "crypto": {}}
    for h in (1, AHEAD):
        out["all"][str(h)] = stats([x for x in rows if x["h"] == h])
        for kind in ("stock", "crypto"):
            out[kind][str(h)] = stats([x for x in rows if x["h"] == h and x["kind"] == kind])
    # what became of the hot names after they were picked, against every name they were picked from
    def after(symbols):
        rs = []
        for s in symbols:
            if s in raw:
                d, c = raw[s]
                i = start_index(d)
                if i:
                    rs.append(c[-1] / c[i - 1] - 1)
        return round(sum(rs) / len(rs), 4) if rs else None
    hot_s, hot_c = hottest(raw)
    out["after"] = {"hotStocks": after([s for _, s in hot_s]), "allStocks": after(STOCKS),
                    "hotCoins": after([s for _, s in hot_c]), "allCoins": after(COINS),
                    "to": max(raw[s][0][-1] for s in raw)}
    # 95% of coin-flippers would land within this many points of 50% on a test this size
    n1 = (out["all"]["1"] or {}).get("calls") or 0
    out["luckBand"] = round(1.96 * math.sqrt(0.25 / n1), 3) if n1 else None
    return out


def main():
    ap = argparse.ArgumentParser(description="Blind short-term forecasting test")
    ap.add_argument("mode", choices=("fetch", "cases", "score"))
    ap.add_argument("--cache", required=True)
    ap.add_argument("--out")
    ap.add_argument("--key")
    ap.add_argument("--cases")
    ap.add_argument("--pred", nargs="*")
    ap.add_argument("--split", type=int, default=2, help="cases: how many forecasters to split the table between")
    a = ap.parse_args()
    if a.mode == "fetch":
        return fetch(a.cache)
    raw = load(a.cache)
    if a.mode == "cases":
        cases, key, picks = make_cases(raw)
        with open(a.out, "w") as f:
            json.dump({"cases": cases, "picks": picks}, f)
        with open(a.key, "w") as f:
            json.dump(key, f)
        for i in range(a.split):
            with open("%s.part%d.txt" % (a.out, i + 1), "w") as f:
                f.write(as_table(cases[i::a.split]))
        print("%d cases (%d stock, %d crypto); hottest stocks %s; hottest coins %s" % (
            len(cases), sum(1 for c in cases if c["kind"] == "stock"), sum(1 for c in cases if c["kind"] == "crypto"),
            picks["stocks"], picks["coins"]))
        return
    with open(a.key) as f:
        key = json.load(f)
    cases = None
    if a.cases:
        with open(a.cases) as f:
            doc = json.load(f)
            cases, picks = doc["cases"], doc["picks"]
    preds = []
    for path in a.pred or []:
        with open(path) as f:
            preds.extend(json.load(f))
    out = score(raw, key, preds, cases)
    if cases:
        out["picks"] = picks
    if a.out:
        with open(a.out, "w") as f:
            json.dump(out, f, separators=(",", ":"))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
