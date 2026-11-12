#!/usr/bin/env python3
"""Assemble the single-file page:  python3 build.py  ->  market-compass.html

The published page is one HTML file. Its parts live in src/ so the engine can
be unit-tested on its own; this script stitches them together.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")


def read(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        return f.read()


LAB_NAMES = {"SPY": "US stocks", "^TA125.TA": "Tel Aviv 125", "BTC-USD": "Bitcoin", "IAU": "Gold",
             "ILS=X": "Dollar in shekels", "hot shares": "Hot shares", "hot coins": "Hot coins"}


def lab_for_page(lab):
    """The few rows of research/forecast_lab.json the Forecasts tab shows: for each market and
    length that is actually forecast, the old rule's score, the new starting figure's, and how
    often the old and new ranges held the price."""
    ranges = {(x["group"], x["days"]): x for x in lab.get("range", [])}
    rows = []
    for x in lab.get("chance", []):
        market = x["group"] in LAB_NAMES and not x["group"].startswith("hot") and x["days"] != 1
        hot = x["group"].startswith("hot") and x["days"] == 1
        if not (market or hot or (x["group"] == "^TA125.TA" and x["days"] == 1)):
            continue
        rg = ranges.get((x["group"], x["days"])) or {}
        rows.append({"name": LAB_NAMES[x["group"]], "days": x["days"], "n": x["n"], "old": x["now"],
                     "start": x["coin"] if x["pick"] == "coin" else x[x["pick"]], "coin": x["pick"] == "coin",
                     "inOld": (rg.get("now") or {}).get("inside"), "inNew": (rg.get("new") or {}).get("inside")})
    return {"symbols": lab.get("symbols"), "firstTestYear": lab.get("firstTestYear"), "rows": rows,
            "telAviv": lab.get("telAviv")}


def main():
    cfg_path = os.path.join(HERE, "config.json")
    config = {}
    if os.path.exists(cfg_path):
        with open(cfg_path, encoding="utf-8") as f:
            config = json.load(f)
    page = read("page.html")
    for token, body in (("/*{{CSS}}*/", read("styles.css")),
                        ("/*{{ENGINE}}*/", read("engine.js")),
                        ("/*{{APP}}*/", read("app.js"))):
        if page.count(token) != 1:
            sys.exit("placeholder %s must appear exactly once" % token)
        if "</script" in body.lower() or "</style" in body.lower():
            sys.exit("a source file contains a closing tag that would end its block early")
        page = page.replace(token, body)
    page = page.replace("/*{{CONFIG}}*/{}", json.dumps(config))
    # Results of the history test (research/backtest.js), shown on the Method tab.
    research = "null"
    res_path = os.path.join(HERE, "..", "research", "results.json")
    if os.path.exists(res_path):
        with open(res_path, encoding="utf-8") as f:
            data = json.load(f)
        blind_path = os.path.join(HERE, "..", "research", "blind_results.json")   # the blind forecasting test
        if os.path.exists(blind_path):
            with open(blind_path, encoding="utf-8") as f:
                data["blind"] = json.load(f)
        lab_path = os.path.join(HERE, "..", "research", "forecast_lab.json")       # where forecasts start, tested
        if os.path.exists(lab_path):
            with open(lab_path, encoding="utf-8") as f:
                data["lab"] = lab_for_page(json.load(f))
        research = json.dumps(data, separators=(",", ":"))
    if page.count("/*{{RESEARCH}}*/null") != 1:
        sys.exit("placeholder /*{{RESEARCH}}*/null must appear exactly once")
    page = page.replace("/*{{RESEARCH}}*/null", research)
    out = os.path.join(HERE, "market-compass.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print("wrote %s (%.0f KB)" % (out, len(page.encode("utf-8")) / 1024.0))


if __name__ == "__main__":
    main()
