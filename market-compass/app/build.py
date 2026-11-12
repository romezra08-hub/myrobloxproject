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
            research = json.dumps(json.load(f), separators=(",", ":"))
    if page.count("/*{{RESEARCH}}*/null") != 1:
        sys.exit("placeholder /*{{RESEARCH}}*/null must appear exactly once")
    page = page.replace("/*{{RESEARCH}}*/null", research)
    out = os.path.join(HERE, "market-compass.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print("wrote %s (%.0f KB)" % (out, len(page.encode("utf-8")) / 1024.0))


if __name__ == "__main__":
    main()
