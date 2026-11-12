#!/usr/bin/env python3
"""Offline tests for the forecast record.  Run:  python3 test_forecasts.py"""
import unittest

import forecasts as fc


def snap(when, **prices):
    assets = {k.replace("BTC", "BTC-USD"): {"px": v, "up1w": 0.55, "up1m": 0.6} for k, v in prices.items()}
    return {"generatedAt": when, "assets": assets}


class Adding(unittest.TestCase):
    def test_the_script_sets_the_price_dates_and_base_rate(self):
        s = snap("2026-11-12T21:10:00Z", SPY=750.0)
        rec, problems = fc.add(fc.empty(), [{"asset": "SPY", "horizonDays": 7, "pUp": 0.58, "low": 730, "high": 770,
                                               "why": "  Rates   are rising. ", "startPx": 1.0, "dueAt": "1999-01-01T00:00:00Z"}], s)
        self.assertEqual(problems, [])
        f = rec["open"][0]
        self.assertEqual(f["startPx"], 750.0)                       # taken from the snapshot, not from the forecaster
        self.assertEqual(f["dueAt"], "2026-11-19T21:10:00Z")
        self.assertEqual(f["madeAt"], "2026-11-12T21:10:00Z")
        self.assertEqual(f["base"], 0.55)
        self.assertEqual(f["why"], "Rates are rising.")
        self.assertEqual(f["name"], "US stocks (SPY fund)")

    def test_certainty_is_not_allowed(self):
        s = snap("2026-11-12T21:10:00Z", SPY=750.0, BTC=70000.0)
        rec, _ = fc.add(fc.empty(), [{"asset": "SPY", "horizonDays": 7, "pUp": 1.0}, {"asset": "BTC-USD", "horizonDays": 30, "pUp": 0}], s)
        got = {f["asset"]: f["pUp"] for f in rec["open"]}
        self.assertEqual(got, {"SPY": 0.95, "BTC-USD": 0.05})

    def test_bad_forecasts_are_refused_with_a_reason(self):
        s = snap("2026-11-12T21:10:00Z", SPY=750.0)
        rec, problems = fc.add(fc.empty(), [
            {"asset": "DOGE", "horizonDays": 7, "pUp": 0.5},
            {"asset": "SPY", "horizonDays": 3, "pUp": 0.5},
            {"asset": "SPY", "horizonDays": 7, "pUp": "likely"},
            {"asset": "SPY", "horizonDays": 7, "pUp": True},
            {"asset": "BTC-USD", "horizonDays": 7, "pUp": 0.5},      # no price for it today
            "nonsense",
        ], s)
        self.assertEqual(rec["open"], [])
        self.assertEqual(len(problems), 6)

    def test_one_forecast_per_asset_horizon_and_day(self):
        s = snap("2026-11-12T21:10:00Z", SPY=750.0)
        rec, _ = fc.add(fc.empty(), [{"asset": "SPY", "horizonDays": 7, "pUp": 0.6}], s)
        again, problems = fc.add(rec, [{"asset": "SPY", "horizonDays": 7, "pUp": 0.2}, {"asset": "SPY", "horizonDays": 30, "pUp": 0.6}], s)
        self.assertEqual(len(again["open"]), 2)
        self.assertEqual([f["pUp"] for f in again["open"] if f["horizonDays"] == 7], [0.6])   # the first call stands
        self.assertEqual(len(problems), 1)

    def test_a_range_nowhere_near_the_price_is_dropped(self):
        s = snap("2026-11-12T21:10:00Z", SPY=750.0)
        rec, _ = fc.add(fc.empty(), [{"asset": "SPY", "horizonDays": 7, "pUp": 0.5, "low": 7, "high": 8}], s)
        self.assertIsNone(rec["open"][0]["low"])
        rec, _ = fc.add(fc.empty(), [{"asset": "SPY", "horizonDays": 7, "pUp": 0.5, "low": 800, "high": 700}], s)
        self.assertIsNone(rec["open"][0]["high"])


class HotNames(unittest.TestCase):
    def snap(self, when, **px):
        s = snap(when, SPY=750.0)
        s["hot"] = {"stocks": ["MU"], "coins": ["TRX-USD"],
                    "assets": {"MU": {"px": px.get("MU", 400.0), "name": "Micron", "kind": "stock", "up1d": 0.56, "up1w": 0.6},
                               "TRX-USD": {"px": px.get("TRX", 0.3), "name": "Tron", "kind": "crypto", "up1d": 0.5},
                               "NVDA": {"px": 180.0, "name": "Nvidia", "kind": "stock", "up1d": 0.55}}}
        return s

    def test_one_day_calls_are_for_todays_hot_names_only(self):
        s = self.snap("2026-11-12T21:10:00Z")
        rec, problems = fc.add(fc.empty(), [
            {"asset": "MU", "horizonDays": 1, "pUp": 0.58},
            {"asset": "TRX-USD", "horizonDays": 1, "pUp": 0.48},
            {"asset": "NVDA", "horizonDays": 1, "pUp": 0.6},        # priced, but not one of today's hot names
            {"asset": "SPY", "horizonDays": 1, "pUp": 0.6},         # a market, not a hot name
            {"asset": "MU", "horizonDays": 7, "pUp": 0.6},          # hot names get one-day calls only
            {"asset": "MU", "horizonDays": 1.5, "pUp": 0.6},
        ], s)
        self.assertEqual(sorted(f["asset"] for f in rec["open"]), ["MU", "TRX-USD"])
        self.assertEqual(len(problems), 4)
        mu = [f for f in rec["open"] if f["asset"] == "MU"][0]
        self.assertEqual((mu["name"], mu["kind"], mu["base"], mu["startPx"]), ("Micron", "stock", 0.56, 400.0))
        self.assertEqual(mu["dueAt"], "2026-11-13T21:10:00Z")

    def test_a_one_day_call_is_scored_at_the_next_refresh_even_if_the_name_has_cooled(self):
        rec, _ = fc.add(fc.empty(), [{"asset": "MU", "horizonDays": 1, "pUp": 0.58}], self.snap("2026-11-12T21:10:00Z"))
        nxt = self.snap("2026-11-13T21:09:00Z", MU=390.0)
        nxt["hot"]["stocks"] = ["NVDA"]                               # no longer a hot name, but still priced
        out = fc.resolve(rec, nxt)
        self.assertEqual(len(out["closed"]), 1)
        self.assertFalse(out["closed"][0]["up"])
        self.assertAlmostEqual(out["closed"][0]["brier"], 0.58 ** 2, places=4)
        self.assertIn(" 1-day calls: right way round 0 of 1", fc.summary(out))

    def test_a_named_news_item_opens_a_call_on_any_well_known_name(self):
        s = self.snap("2026-11-12T21:10:00Z")
        rec, problems = fc.add(fc.empty(), [
            {"asset": "NVDA", "horizonDays": 1, "pUp": 0.47, "news": "  Chief executive   resigned today "},
            {"asset": "MU", "horizonDays": 1, "pUp": 0.55, "news": "Raised its sales forecast"},
            {"asset": "TRX-USD", "horizonDays": 1, "pUp": 0.5},
            {"asset": "TSLA", "horizonDays": 1, "pUp": 0.5, "news": "Something"},      # not priced in the snapshot at all
        ], s)
        by = {f["asset"]: f for f in rec["open"]}
        self.assertEqual(sorted(by), ["MU", "NVDA", "TRX-USD"])
        self.assertEqual((by["NVDA"]["news"], by["NVDA"]["onNews"], by["NVDA"]["extra"], by["NVDA"]["name"]), ("Chief executive resigned today", True, True, "Nvidia"))
        self.assertEqual((by["MU"]["onNews"], by["MU"]["extra"]), (True, False))          # a hot name can rest on news too
        self.assertEqual((by["TRX-USD"]["onNews"], by["TRX-USD"]["news"]), (False, None))
        self.assertEqual(len(problems), 1)

    def test_only_three_news_only_calls_a_day(self):
        s = self.snap("2026-11-12T21:10:00Z")
        for sym in ("AAA", "BBB", "CCC", "DDD"):
            s["hot"]["assets"][sym] = {"px": 10.0, "name": sym, "kind": "stock", "up1d": 0.5}
        items = [{"asset": sym, "horizonDays": 1, "pUp": 0.5, "news": "x"} for sym in ("AAA", "BBB", "CCC", "DDD")]
        rec, problems = fc.add(fc.empty(), items, s)
        self.assertEqual(sorted(f["asset"] for f in rec["open"]), ["AAA", "BBB", "CCC"])
        self.assertIn("only 3 news calls a day", problems[0])
        rec2, problems2 = fc.add(rec, [{"asset": "DDD", "horizonDays": 1, "pUp": 0.5, "news": "x"}], s)   # a later attempt the same day
        self.assertEqual(len(rec2["open"]), 3)
        nxt = self.snap("2026-11-13T21:10:00Z")
        nxt["hot"]["assets"]["DDD"] = {"px": 10.0, "name": "DDD", "kind": "stock", "up1d": 0.5}
        rec3, _ = fc.add(rec, [{"asset": "DDD", "horizonDays": 1, "pUp": 0.5, "news": "x"}], nxt)          # a new day, a new allowance
        self.assertEqual(len(rec3["open"]), 4)

    def test_a_friday_call_waits_for_monday(self):
        rec, _ = fc.add(fc.empty(), [{"asset": "MU", "horizonDays": 1, "pUp": 0.58}], self.snap("2026-11-13T21:10:00Z"))
        self.assertEqual(len(fc.resolve(rec, self.snap("2026-11-14T09:00:00Z"))["closed"]), 0)
        out = fc.resolve(rec, self.snap("2026-11-16T21:09:00Z", MU=410.0))
        self.assertTrue(out["closed"][0]["up"])
        self.assertFalse(out["closed"][0]["late"])


class Learning(unittest.TestCase):
    def closed(self, n, p, base, ups):
        return [{"asset": "SPY", "horizonDays": 7, "pUp": p, "base": base, "up": (i % 10) < ups, "inRange": True} for i in range(n)]

    def test_no_correction_on_a_short_record(self):
        self.assertEqual(fc.trust(self.closed(59, 0.7, 0.5, 7)), (None, 59))
        self.assertEqual(fc.trust([]), (None, 0))

    def test_departures_that_were_right_are_kept_and_noise_is_shrunk_away(self):
        k, n = fc.trust(self.closed(100, 0.7, 0.5, 7))          # said 70%, usual 50%, rose 70% of the time
        self.assertEqual((k, n), (1.0, 100))
        k, _ = fc.trust(self.closed(100, 0.7, 0.5, 5))          # said 70%, it rose only the usual 50%
        self.assertEqual(k, 0.0)
        k, _ = fc.trust(self.closed(100, 0.7, 0.5, 6))          # half as right as claimed
        self.assertAlmostEqual(k, 0.5)
        k, _ = fc.trust(self.closed(100, 0.7, 0.5, 3))          # worse than useless is treated as useless
        self.assertEqual(k, 0.0)
        self.assertEqual(fc.trust(self.closed(100, 0.5, 0.5, 5))[0], None)   # never departed: nothing to learn from

    def test_new_calls_carry_the_correction_once_there_is_a_record(self):
        s = snap("2026-11-12T21:10:00Z", SPY=750.0)
        rec = fc.empty()
        rec["closed"] = self.closed(100, 0.7, 0.5, 6)
        for i, f in enumerate(rec["closed"]):
            f["id"] = "old%d" % i
        out, _ = fc.add(rec, [{"asset": "SPY", "horizonDays": 7, "pUp": 0.65}], s)
        f = out["open"][0]
        self.assertEqual(out["trust"], {"k": 0.5, "n": 100})
        self.assertEqual((f["pUp"], f["base"], f["pAdj"]), (0.65, 0.55, 0.6))     # half of the 10-point departure
        fresh, _ = fc.add(fc.empty(), [{"asset": "SPY", "horizonDays": 7, "pUp": 0.65}], s)
        self.assertNotIn("pAdj", fresh["open"][0])
        self.assertIsNone(fresh["trust"])
        done = fc.resolve(out, snap("2026-11-19T21:10:00Z", SPY=760.0))
        self.assertAlmostEqual([x for x in done["closed"] if x.get("pAdj")][0]["adjBrier"], 0.16)
        self.assertEqual(done["trust"], {"k": 0.5, "n": 100})

    def test_feedback_gives_totals_and_no_single_call(self):
        self.assertIn("too few", fc.feedback(fc.empty()))
        rec = fc.empty()
        rec["closed"] = self.closed(100, 0.7, 0.5, 5)
        text = fc.feedback(rec)
        self.assertIn("you said 70% on average, the usual figure was 50%, it rose 50% of the time", text)
        self.assertIn("you were worse", text)
        self.assertIn("added nothing", text)
        for i, f in enumerate(rec["closed"]):
            f["onNews"] = i < 30
        text = fc.feedback(rec)
        self.assertRegex(text, r"calls resting on a named news item\s+30 calls")
        self.assertIn("calls with no named news item", text)
        self.assertNotIn("why", text)

    def test_three_month_calls_are_allowed_for_the_five_markets(self):
        s = snap("2026-11-12T21:10:00Z", SPY=750.0)
        s["assets"]["SPY"]["up3m"] = 0.7
        rec, problems = fc.add(fc.empty(), [{"asset": "SPY", "horizonDays": 90, "pUp": 0.66}], s)
        self.assertEqual(problems, [])
        self.assertEqual((rec["open"][0]["base"], rec["open"][0]["dueAt"]), (0.7, "2027-02-10T21:10:00Z"))


class Loading(unittest.TestCase):
    def test_a_missing_or_wrapped_record_loads(self):
        import json, os, tempfile
        self.assertEqual(fc.load("/no/such/file.json"), fc.empty())
        self.assertEqual(fc.load(None), fc.empty())
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "f.json")
            for doc in ({"open": [{"id": "x"}], "closed": [], "updatedAt": "t"}, {"data": {"open": [{"id": "x"}], "closed": []}, "version": 3}):
                with open(p, "w") as f:
                    json.dump(doc, f)
                self.assertEqual(fc.load(p)["open"], [{"id": "x"}])
            with open(p, "w") as f:
                json.dump([1, 2], f)
            self.assertEqual(fc.load(p), fc.empty())


class Resolving(unittest.TestCase):
    def setUp(self):
        s = snap("2026-11-12T21:10:00Z", SPY=750.0, BTC=70000.0)
        self.rec, _ = fc.add(fc.empty(), [
            {"asset": "SPY", "horizonDays": 7, "pUp": 0.7, "low": 730, "high": 770},
            {"asset": "BTC-USD", "horizonDays": 7, "pUp": 0.4, "low": 60000, "high": 76000},
            {"asset": "SPY", "horizonDays": 30, "pUp": 0.6},
        ], s)

    def test_nothing_resolves_before_it_is_due(self):
        out = fc.resolve(self.rec, snap("2026-11-18T21:10:00Z", SPY=800.0, BTC=1.0))
        self.assertEqual((len(out["open"]), len(out["closed"])), (3, 0))

    def test_due_forecasts_are_scored_from_the_snapshot_price(self):
        out = fc.resolve(self.rec, snap("2026-11-19T21:12:00Z", SPY=760.0, BTC=65000.0))
        self.assertEqual(len(out["open"]), 1)                                      # the 30-day one waits
        by = {f["asset"]: f for f in out["closed"]}
        self.assertTrue(by["SPY"]["up"])
        self.assertAlmostEqual(by["SPY"]["brier"], 0.09)                           # said 70%, it rose: (0.7 - 1)^2
        self.assertAlmostEqual(by["SPY"]["baseBrier"], (0.55 - 1) ** 2)
        self.assertTrue(by["SPY"]["inRange"])
        self.assertFalse(by["BTC-USD"]["up"])
        self.assertAlmostEqual(by["BTC-USD"]["brier"], 0.16)                       # said 40% up, it fell: (0.4 - 0)^2
        self.assertAlmostEqual(by["BTC-USD"]["change"], 65000.0 / 70000.0 - 1, places=5)
        self.assertFalse(by["SPY"]["late"])

    def test_a_refresh_a_few_minutes_early_still_scores_the_call(self):
        out = fc.resolve(self.rec, snap("2026-11-19T21:08:30Z", SPY=760.0, BTC=65000.0))   # made at 21:10 a week before
        self.assertEqual(len(out["closed"]), 2)
        early = fc.resolve(self.rec, snap("2026-11-19T12:00:00Z", SPY=760.0, BTC=65000.0))  # but not half a day early
        self.assertEqual(len(early["closed"]), 0)

    def test_an_unchanged_price_counts_as_not_up(self):
        out = fc.resolve(self.rec, snap("2026-11-20T21:10:00Z", SPY=750.0, BTC=70000.0))
        self.assertTrue(all(not f["up"] for f in out["closed"]))

    def test_a_missing_price_leaves_the_forecast_open(self):
        out = fc.resolve(self.rec, snap("2026-11-20T21:10:00Z", SPY=760.0))
        self.assertEqual(sorted(f["asset"] for f in out["open"]), ["BTC-USD", "SPY"])
        self.assertEqual([f["asset"] for f in out["closed"]], ["SPY"])

    def test_a_refresh_that_ran_days_late_is_marked(self):
        out = fc.resolve(self.rec, snap("2026-11-25T21:10:00Z", SPY=760.0, BTC=65000.0))
        self.assertTrue(all(f["late"] for f in out["closed"]))

    def test_resolving_twice_changes_nothing(self):
        once = fc.resolve(self.rec, snap("2026-11-19T21:12:00Z", SPY=760.0, BTC=65000.0))
        twice = fc.resolve(once, snap("2026-11-20T21:12:00Z", SPY=100.0, BTC=1.0))
        self.assertEqual(once["closed"], twice["closed"])

    def test_the_summary_counts_calls_the_right_way_round(self):
        out = fc.resolve(self.rec, snap("2026-11-19T21:12:00Z", SPY=760.0, BTC=65000.0))
        self.assertIn("right way round 2 of 2", fc.summary(out))


if __name__ == "__main__":
    unittest.main(verbosity=1)
