#!/usr/bin/env python3
"""Offline tests for the pure maths in refresh.py.  Run:  python3 test_refresh.py"""
import math
import unittest

import refresh as r


def ramp(n, start=100.0, daily=0.001):
    return [start * (1 + daily) ** i for i in range(n)]


def dates(n):
    import datetime as dt
    d0 = dt.date(2025, 1, 1)
    return [(d0 + dt.timedelta(days=i)).isoformat() for i in range(n)]


class Helpers(unittest.TestCase):
    def test_clamp_and_soft(self):
        self.assertEqual(r.clamp(3), 1.0)
        self.assertEqual(r.clamp(-3), -1.0)
        self.assertAlmostEqual(r.soft(0.02, 0.04), 0.5)
        self.assertEqual(r.soft(0.5, 0.04), 1.0)
        self.assertEqual(r.soft(-0.5, 0.04), -1.0)
        self.assertIsNone(r.soft(None, 0.04))

    def test_sma_ret_pct(self):
        s = [1, 2, 3, 4, 5]
        self.assertEqual(r.sma(s, 5), 3)
        self.assertEqual(r.sma(s, 2), 4.5)
        self.assertIsNone(r.sma(s, 6))
        self.assertAlmostEqual(r.ret(s, 1), 0.25)
        self.assertIsNone(r.ret(s, 5))
        self.assertIsNone(r.pct(1, 0))
        self.assertIsNone(r.pct(None, 2))

    def test_realized_vol_matches_known_series(self):
        # alternating +1% / -1% log returns: stdev is ~1% a day, ~15.9% a year at 252 days
        s = [100.0]
        for i in range(60):
            s.append(s[-1] * math.exp(0.01 if i % 2 == 0 else -0.01))
        v = r.realized_vol(s, 60, 252)
        self.assertAlmostEqual(v, 0.01 * math.sqrt(252) * math.sqrt(60 / 59), places=4)
        self.assertIsNone(r.realized_vol([1, 2], 20, 252))

    def test_percentile_and_downsample(self):
        self.assertEqual(r.percentile_rank([1, 2, 3, 4], 4), 100.0)
        self.assertEqual(r.percentile_rank([1, 2, 3, 4], 1), 25.0)
        d = r.downsample(list(range(100)), 10)
        self.assertEqual(len(d), 10)
        self.assertEqual(d[0], 0)
        self.assertEqual(d[-1], 99)
        self.assertEqual(r.downsample([1, 2, 3], 10), [1, 2, 3])

    def test_sig_keeps_precision_at_any_scale(self):
        self.assertEqual(r.sig(71888.234, 6), 71888.2)
        self.assertEqual(r.sig(0.0659941, 5), 0.065994)
        self.assertEqual(r.sig(0), 0)

    def test_labels(self):
        self.assertEqual(r.label_for(0.6), "Favorable")
        self.assertEqual(r.label_for(0.2), "Leaning positive")
        self.assertEqual(r.label_for(0.0), "Neutral")
        self.assertEqual(r.label_for(-0.2), "Leaning negative")
        self.assertEqual(r.label_for(-0.9), "Unfavorable")
        self.assertEqual(r.label_for(None), "No reading")


class Analysis(unittest.TestCase):
    def test_steady_uptrend_scores_fully_positive(self):
        n = 520
        a = r.analyze(dates(n), ramp(n), ppy=252)
        self.assertGreater(a["vs200"], 0)
        self.assertGreater(a["cross"], 0)
        self.assertAlmostEqual(a["ret12m"], (1.001 ** 252) - 1, places=3)
        self.assertEqual(a["dd52"], 0)
        score = r.combine(r.trend_parts(a, cash12m=0.04))
        self.assertGreater(score, 0.9)

    def test_steady_downtrend_scores_fully_negative(self):
        n = 520
        a = r.analyze(dates(n), ramp(n, daily=-0.001), ppy=252)
        self.assertLess(a["vs200"], 0)
        self.assertLess(a["dd52"], -0.2)
        score = r.combine(r.trend_parts(a, cash12m=0.04))
        self.assertLess(score, -0.9)

    def test_flat_market_loses_to_cash(self):
        n = 520
        flat = [100.0 + (0.01 if i % 2 else -0.01) for i in range(n)]
        a = r.analyze(dates(n), flat, ppy=252)
        parts = {p["id"]: p for p in r.trend_parts(a, cash12m=0.04)}
        self.assertLess(parts["mom12"]["score"], 0)       # flat price, but T-bills paid 4%
        self.assertAlmostEqual(parts["vs200"]["score"], 0, delta=0.05)

    def test_total_return_series_drives_returns_but_not_price(self):
        n = 520
        px = [100.0] * n
        tr = ramp(n, daily=0.0002)  # all the return comes from income
        a = r.analyze(dates(n), px, tr, ppy=252)
        self.assertEqual(a["px"], 100.0)
        self.assertGreater(a["ret12m"], 0.04)

    def test_short_history_degrades_without_crashing(self):
        # 40 days: not enough for any of the four readings, so there is no score at all
        a = r.analyze(dates(40), ramp(40), ppy=252)
        self.assertIsNone(a["vs200"])
        self.assertIsNone(a["ret12m"])
        self.assertIsNone(r.combine(r.trend_parts(a, cash12m=0.04)))
        # 100 days: only the 3-month return exists, and the score falls back to it alone
        a = r.analyze(dates(100), ramp(100), ppy=252)
        self.assertIsNone(a["vs200"])
        parts = r.trend_parts(a, cash12m=0.04)
        self.assertEqual([p["id"] for p in parts if p["score"] is not None], ["mom3"])
        self.assertGreater(r.combine(parts), 0)
        self.assertIsNone(r.combine([{"score": None, "weight": 1.0}]))

    def test_combine_reweights_missing_parts(self):
        parts = [{"score": 1.0, "weight": 0.5}, {"score": None, "weight": 0.5}]
        self.assertEqual(r.combine(parts), 1.0)
        parts = [{"score": 1.0, "weight": 0.5}, {"score": -1.0, "weight": 0.5}]
        self.assertEqual(r.combine(parts), 0.0)


class Headlines(unittest.TestCase):
    def test_rank_prefers_newsrooms_and_drops_filler(self):
        self.assertEqual(r.headline_rank({"src": "Reuters", "title": "Fed holds rates"}), 0)
        self.assertEqual(r.headline_rank({"src": "Some Local Paper", "title": "Fed holds rates"}), 1)
        self.assertIsNone(r.headline_rank({"src": "MarketBeat", "title": "Acme issues earnings results"}))
        self.assertIsNone(r.headline_rank({"src": "Reuters", "title": "Dogecoin price prediction for 2030"}))


if __name__ == "__main__":
    unittest.main(verbosity=1)
