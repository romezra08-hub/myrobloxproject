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


class Readings(unittest.TestCase):
    def test_trend_weights_and_dropped_cross(self):
        a = r.analyze(dates(520), ramp(520), ppy=252)
        parts = r.trend_parts(a, cash12m=0.04)
        self.assertEqual([p["id"] for p in parts], ["vs200", "mom12", "mom3"])
        self.assertAlmostEqual(sum(p["weight"] for p in parts), 1.0)
        self.assertEqual(parts[0]["weight"], parts[1]["weight"])      # the two slow readings count equally

    def test_crypto_trend_leans_on_shorter_horizons(self):
        a = r.analyze(dates(730), ramp(730, daily=0.002), ppy=365)
        parts = {p["id"]: p for p in r.crypto_trend_parts(a, cash12m=0.04)}
        self.assertEqual(set(parts), {"vs50", "vs100", "vs200", "mom1", "mom3", "mom12"})
        self.assertAlmostEqual(sum(p["weight"] for p in parts.values()), 1.0)
        self.assertEqual(parts["mom12"]["weight"], 0.10)              # the 12-month rule is unproven for crypto
        self.assertGreater(r.combine(list(parts.values())), 0.9)
        down = r.analyze(dates(730), ramp(730, daily=-0.002), ppy=365)
        self.assertLess(r.combine(r.crypto_trend_parts(down, cash12m=0.04)), -0.9)

    def test_valuation_is_neutral_across_the_middle_of_its_own_range(self):
        hist = [("%04d-%02d-01" % (1980 + i // 12, i % 12 + 1), 10 + i * 0.05) for i in range(12 * 46)]   # steadily rising
        last = hist[-1][1]
        s_top, p_top = r.valuation_reading(hist, last)
        self.assertEqual(p_top, 100.0)
        self.assertEqual(s_top, -1.0)
        window = sorted(v for d, v in hist if d >= "1985-12-01")
        mid = window[len(window) // 2]
        self.assertEqual(r.valuation_reading(hist, mid)[0], 0.0)
        s_low, p_low = r.valuation_reading(hist, window[0])
        self.assertLess(p_low, 5)
        self.assertEqual(s_low, 1.0)
        # between the 80th and 95th percentile it slides from 0 to -1
        s87, p87 = r.valuation_reading(hist, window[int(len(window) * 0.875)])
        self.assertTrue(-0.7 < s87 < -0.3, s87)
        # values older than 40 years do not count
        old = [("1900-01-01", 500.0)] + hist
        self.assertEqual(r.valuation_reading(old, last)[1], 100.0)
        self.assertEqual(r.valuation_reading([], 20), (None, None))
        self.assertEqual(r.valuation_reading(hist[:30], 12), (None, None))

    def test_volatility_reading(self):
        self.assertEqual(r.volatility_reading(0.16, 0.16), 0)
        self.assertAlmostEqual(r.volatility_reading(0.24, 0.16), -0.5)
        self.assertEqual(r.volatility_reading(0.60, 0.16), -1.0)       # capped
        self.assertAlmostEqual(r.volatility_reading(0.12, 0.16), 0.25)
        self.assertEqual(r.volatility_reading(0.02, 0.16), 0.5)        # calm earns only half credit
        self.assertIsNone(r.volatility_reading(None, 0.16))

    def test_rate_shock_reading(self):
        self.assertEqual(r.rate_shock_reading(0.25), 0)                # small rises are ignored
        self.assertAlmostEqual(r.rate_shock_reading(0.625), -0.5)
        self.assertEqual(r.rate_shock_reading(1.5), -1.0)
        self.assertEqual(r.rate_shock_reading(0.0), 0)
        self.assertAlmostEqual(r.rate_shock_reading(-0.3), 0.3)
        self.assertEqual(r.rate_shock_reading(-2.0), 0.5)              # falling yields earn at most half
        self.assertIsNone(r.rate_shock_reading(None))

    def test_inflation_regime_counts_four_tests(self):
        hot = r.inflation_regime(3.7, 3.3, 0.35, 0.43)
        self.assertEqual((hot["points"], hot["mode"]), (4, "short"))
        calm = r.inflation_regime(2.1, 2.4, -0.3, -0.25)
        self.assertEqual((calm["points"], calm["mode"]), (0, "normal"))
        two = r.inflation_regime(3.2, 3.4, 0.3, 0.0)
        self.assertEqual((two["points"], two["mode"]), (2, "mixed"))
        self.assertEqual(r.inflation_regime(3.2, 3.0, None, None)["mode"], "mixed")
        blind = r.inflation_regime(None, None, None, 0.5)              # one known test is not enough to call it
        self.assertIsNone(blind["mode"])
        self.assertEqual(len(hot["tests"]), 4)


class Risk(unittest.TestCase):
    def test_pearson_known_values(self):
        self.assertAlmostEqual(r.pearson([1, 2, 3, 4], [2, 4, 6, 8]), 1.0)
        self.assertAlmostEqual(r.pearson([1, 2, 3, 4], [8, 6, 4, 2]), -1.0)
        self.assertAlmostEqual(r.pearson([1, 2, 3, 4, 5], [2, 1, 4, 3, 5]), 0.8)
        self.assertIsNone(r.pearson([1, 1, 1], [1, 2, 3]))      # no variation: undefined
        self.assertIsNone(r.pearson([1, 2], [1, 2]))            # too short to mean anything

    def test_weekly_returns_align_series_with_different_calendars(self):
        import datetime as dt
        d0 = dt.date(2025, 1, 6)                                # a Monday
        every = [(d0 + dt.timedelta(days=i)).isoformat() for i in range(140)]
        weekdays = [d for d in every if dt.date.fromisoformat(d).weekday() < 5]
        named = {"coin": (every, [100 * 1.01 ** i for i in range(len(every))]),
                 "fund": (weekdays, [50 * 1.002 ** i for i in range(len(weekdays))])}
        rets, first, last = r.weekly_log_returns(named, step=5)
        self.assertEqual(len(rets["coin"]), len(rets["fund"]))
        self.assertEqual(last, weekdays[-1])                    # anchored on the latest shared date
        self.assertAlmostEqual(rets["fund"][-1], 5 * math.log(1.002), places=9)   # 5 trading days
        self.assertAlmostEqual(rets["coin"][-1], 7 * math.log(1.01), places=9)    # the same 7 calendar days

    def test_risk_table_recovers_volatility_and_correlation(self):
        import random
        rng = random.Random(7)
        n = 5 * 260
        a = [rng.gauss(0, 0.01) for _ in range(n)]
        b = [0.5 * x + rng.gauss(0, 0.01) for x in a]           # built to correlate about 0.45 with a
        dts = dates(n + 1)
        def path(steps):
            v = [100.0]
            for s_ in steps:
                v.append(v[-1] * math.exp(s_))
            return v
        t = r.risk_table({"a": (dts, path(a)), "b": (dts, path(b)), "c": (dts, path([-x for x in a]))})
        self.assertEqual(t["weeks"], 260)
        self.assertAlmostEqual(t["vol"]["a"], 0.01 * math.sqrt(5 * 52), delta=0.02)
        self.assertEqual(t["corr"]["a"]["a"], 1.0)
        self.assertAlmostEqual(t["corr"]["a"]["b"], 0.447, delta=0.1)
        self.assertAlmostEqual(t["corr"]["a"]["c"], -1.0, places=3)
        self.assertEqual(t["corr"]["a"]["b"], t["corr"]["b"]["a"])
        self.assertIsNone(r.risk_table({"a": (dts[:60], path(a)[:60])}))   # under half a year: no table


class BaseRates(unittest.TestCase):
    def test_share_up_counts_rising_stretches(self):
        self.assertEqual(r.share_up(ramp(300), 5), 1.0)
        self.assertEqual(r.share_up(ramp(300, daily=-0.001), 5), 0.0)
        zig = [100 + (i % 2) for i in range(301)]                 # up one day, down the next
        self.assertAlmostEqual(r.share_up(zig, 1), 0.5)
        self.assertEqual(r.share_up(zig, 2), 0.0)                 # two days on, it is always back where it was
        self.assertIsNone(r.share_up(ramp(40), 5))                # too little history to call a base rate

    def test_typical_range_widens_with_time_and_swing(self):
        lo7, hi7 = r.typical_range(100.0, 0.20, 7)
        lo30, hi30 = r.typical_range(100.0, 0.20, 30)
        self.assertTrue(lo30 < lo7 < 100.0 < hi7 < hi30)
        sd = 0.20 * math.sqrt(7 / 365.0)
        self.assertAlmostEqual(hi7, 100.0 * math.exp(1.2816 * sd), places=2)
        self.assertAlmostEqual(lo7 * hi7, 100.0 ** 2, delta=0.5)        # even odds either side, in ratio terms
        self.assertGreater(r.typical_range(100.0, 0.40, 7)[1], hi7)
        self.assertIsNone(r.typical_range(100.0, None, 7))
        self.assertIsNone(r.typical_range(None, 0.2, 7))

    def test_hot_picks_are_the_best_twelve_months(self):
        table = {"A": {"ret12m": 0.5}, "B": {"ret12m": 2.0}, "C": {"ret12m": None}, "D": {"ret12m": -0.1}, "E": {}}
        self.assertEqual(r.hot_picks(table, ["A", "B", "C", "D", "E", "missing"], 2), ["B", "A"])
        self.assertEqual(r.hot_picks(table, ["A", "B", "C", "D"], 5), ["B", "A", "D"])
        self.assertEqual(r.hot_picks({}, ["A"]), [])
        self.assertFalse(set(r.HOT_STOCKS) & set(r.HOT_COINS))
        self.assertTrue(all(k.endswith("-USD") for k in r.HOT_COINS))

    def test_max_drawdown_is_the_deepest_fall_from_a_high(self):
        self.assertEqual(r.max_drawdown([100, 110, 120]), 0.0)
        self.assertAlmostEqual(r.max_drawdown([100, 120, 90, 130, 117]), 90 / 120.0 - 1)
        self.assertAlmostEqual(r.max_drawdown([100, 50, 200, 100]), -0.5)
        self.assertEqual(r.max_drawdown([]), 0.0)

    def test_analyze_reports_two_year_return_swing_and_worst_fall(self):
        a = r.analyze(dates(505), ramp(505))                     # two years at 0.1% a day
        self.assertAlmostEqual(a["annAll"], 1.001 ** 252 - 1, places=3)
        self.assertEqual(a["mdd"], 0.0)
        self.assertLess(a["volAll"], 0.001)
        self.assertIsNone(r.analyze(dates(120), ramp(120))["annAll"])   # under a year: no yearly figure

    def test_analyze_reports_weekly_and_monthly_base_rates(self):
        a = r.analyze(dates(400), ramp(400))
        self.assertEqual((a["up1w"], a["up1m"], a["up1d"], a["up3m"]), (1.0, 1.0, 1.0, 1.0))


class Israel(unittest.TestCase):
    def test_bond_index_earns_the_yield_when_nothing_moves(self):
        idx = r.bond_index([4.0] * 13, 4.8)
        self.assertEqual(len(idx), 13)
        self.assertAlmostEqual(idx[-1] / idx[0] - 1, (1 + 0.04 / 12) ** 12 - 1, places=9)

    def test_bond_index_loses_duration_times_a_rise_in_yield(self):
        idx = r.bond_index([4.0, 5.0], 4.8)
        self.assertAlmostEqual(idx[1] / idx[0] - 1, 0.04 / 12 - 0.048, places=9)
        up = r.bond_index([4.0, 3.5], 4.8)
        self.assertGreater(up[1], up[0] * 1.02)   # a fall in yield is a gain

    def test_monthly_trend_matches_the_daily_weights_and_direction(self):
        falling = r.bond_index([5.0 - 0.1 * i for i in range(20)], 4.8)   # yields falling: prices rising
        parts = r.monthly_trend_parts(falling, 0.03)
        self.assertEqual([p["id"] for p in parts], ["vs10m", "mom12", "mom3"])
        self.assertAlmostEqual(sum(p["weight"] for p in parts), 1.0)
        self.assertTrue(all(p["score"] > 0 for p in parts))
        rising = r.bond_index([3.0 + 0.1 * i for i in range(20)], 4.8)
        self.assertLess(r.combine(r.monthly_trend_parts(rising, 0.03)), -0.5)
        self.assertEqual(r.monthly_trend_parts(falling[:12], 0.03), [])   # under a year: no reading

    def test_monthly_trend_measures_against_cash(self):
        flat = r.bond_index([4.0] * 20, 4.8)                              # earns about 4.1% a year
        by_id = lambda parts: {p["id"]: p for p in parts}
        self.assertGreater(by_id(r.monthly_trend_parts(flat, 0.02))["mom12"]["score"], 0)
        self.assertLess(by_id(r.monthly_trend_parts(flat, 0.06))["mom12"]["score"], 0)
        self.assertIsNone(by_id(r.monthly_trend_parts(flat, None))["mom12"]["score"])

    def test_inflation_is_read_against_the_target_band(self):
        self.assertAlmostEqual(r.target_inflation_reading(2.0, 2.0), 0.0)            # middle of 1 to 3, steady
        self.assertGreater(r.target_inflation_reading(1.0, 1.0), 0)                  # low inflation suits bonds
        self.assertLess(r.target_inflation_reading(3.5, 3.5), 0)
        self.assertAlmostEqual(r.target_inflation_reading(3.5, 3.5), -0.5)           # full level penalty, no direction
        self.assertAlmostEqual(r.target_inflation_reading(4.5, 3.5), -1.0)           # high and rising
        self.assertGreater(r.target_inflation_reading(2.5, 3.2), r.target_inflation_reading(2.5, 2.5))  # falling helps
        self.assertAlmostEqual(r.target_inflation_reading(3.5, None), -0.5)          # no history counts as no change
        self.assertIsNone(r.target_inflation_reading(None, 2.0))

    def test_sdmx_csv_is_grouped_sorted_and_tolerant(self):
        text = ("SERIES_CODE,FREQ,TIME_PERIOD,OBS_VALUE\n"
                "A,M,2026-02,3.5\nA,M,2026-01,3.4\nB,M,2026-01,1.1\nA,M,2026-03,\nB,M,2026-02,oops\n")
        got = r.parse_sdmx_csv(text)
        self.assertEqual(got["A"], [("2026-01", 3.4), ("2026-02", 3.5)])
        self.assertEqual(got["B"], [("2026-01", 1.1)])
        self.assertEqual(r.parse_sdmx_csv("<html>blocked</html>"), {})

    def test_month_name(self):
        self.assertEqual(r.month_name("2026-09"), "September 2026")
        self.assertEqual(r.month_name("soon"), "soon")
        self.assertIsNone(r.month_name(None))

    def test_align_monthly_keeps_shared_months_only(self):
        months, cols = r.align_monthly({"a": [("2026-01", 1.0), ("2026-02", 2.0), ("2026-03", 3.0)],
                                        "b": [("2026-02", 20.0), ("2026-03", 30.0), ("2026-04", 40.0)]})
        self.assertEqual(months, ["2026-02", "2026-03"])
        self.assertEqual(cols, {"a": [2.0, 3.0], "b": [20.0, 30.0]})
        self.assertEqual(r.align_monthly({"a": [("2026-01", 1.0)], "b": []}), ([], {}))


class Headlines(unittest.TestCase):
    def test_rank_prefers_newsrooms_and_drops_filler(self):
        self.assertEqual(r.headline_rank({"src": "Reuters", "title": "Fed holds rates"}), 0)
        self.assertEqual(r.headline_rank({"src": "Some Local Paper", "title": "Fed holds rates"}), 1)
        self.assertIsNone(r.headline_rank({"src": "MarketBeat", "title": "Acme issues earnings results"}))
        self.assertIsNone(r.headline_rank({"src": "Reuters", "title": "Dogecoin price prediction for 2030"}))


if __name__ == "__main__":
    unittest.main(verbosity=1)
