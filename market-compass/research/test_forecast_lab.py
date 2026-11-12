#!/usr/bin/env python3
"""Tests for forecast_lab.py: above all, that nothing it scores has seen the future.

    python3 test_forecast_lab.py        (needs numpy)
"""
import datetime as dt
import unittest

import numpy as np

import forecast_lab as lab


def walk(seed, n=2600, start=dt.date(2012, 1, 2), drift=0.0003, swing=0.012):
    rng = np.random.default_rng(seed)
    days, d = [], start
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += dt.timedelta(days=1)
    px = 100 * np.exp(np.cumsum(rng.normal(drift, swing, n)))
    return days, [float(v) for v in px]


def world(change_after=None):
    """Six made-up funds. With change_after, every price after that date is replaced by a crash."""
    out = {}
    for i in range(6):
        days, px = walk(i)
        if change_after:
            px = [p if d <= change_after else p * 0.5 for d, p in zip(days, px)]
        out["F%d" % i] = lab.Asset("F%d" % i, "fund", days, px)
    return out


class NoPeeking(unittest.TestCase):
    def test_nothing_scored_before_a_date_depends_on_prices_after_it(self):
        cut = "2019-06-28"
        for days in (1, 7, 30):
            a = lab.walk_forward(lab.table(world(), "fund", days), days)
            b = lab.walk_forward(lab.table(world(change_after=cut), "fund", days), days)
            before = a["day"] <= int(cut.replace("-", ""))
            self.assertTrue(np.array_equal(a["day"][before], b["day"][b["day"] <= int(cut.replace("-", ""))]))
            same = b["day"] <= int(cut.replace("-", ""))
            for col in ("now", "own", "pool", "shrunk", "model", "lo", "hi"):
                x, y = a[col][before], b[col][same]
                self.assertTrue(np.allclose(x, y, equal_nan=True), "%s for %d days saw the future" % (col, days))
            self.assertGreater(int((~np.isnan(a["model"][before])).sum()), 1000)     # and the comparison is not empty

    def test_the_old_rule_is_the_share_of_rises_in_the_window(self):
        a = world()["F0"]
        k, up, _ = a.outcome(7)
        t = 1500
        self.assertEqual(k, 5)
        self.assertAlmostEqual(a.now_rate(7)[t], np.mean([a.p[i + k] > a.p[i] for i in range(t - 504, t - k + 1)]))
        ups, n = a.own_rate(7)
        self.assertEqual((ups[t], n[t]), (sum(a.p[i + k] > a.p[i] for i in range(0, t - k + 1)), t - k + 1))


class Pieces(unittest.TestCase):
    def test_rolling_swing_matches_the_plain_formula(self):
        rng = np.random.default_rng(1)
        r_ = rng.normal(0, 0.01, 300)
        self.assertAlmostEqual(lab.roll_sd(r_, 20)[-1], np.std(r_[-20:], ddof=1), places=10)
        self.assertTrue(np.isnan(lab.roll_sd(r_, 20)[18]))

    def test_the_fit_finds_a_real_tilt_and_ignores_noise(self):
        rng = np.random.default_rng(2)
        x = rng.normal(0, 1, (20000, 2))
        y = (rng.random(20000) < 1 / (1 + np.exp(-(0.2 + 0.5 * x[:, 0])))).astype(float)
        w = lab.fit_logistic(x, y, np.zeros(20000), ridge=1.0)
        self.assertAlmostEqual(w[0], 0.2, delta=0.05)
        self.assertAlmostEqual(w[1], 0.5, delta=0.05)
        self.assertAlmostEqual(w[2], 0.0, delta=0.05)

    def test_bars_ahead_match_the_pipeline(self):
        self.assertEqual([lab.bars_for(d, 252) for d in lab.DAYS], [1, 5, 21, 62])
        self.assertEqual([lab.bars_for(d, 365) for d in lab.DAYS], [1, 7, 30, 90])

    def test_the_us_move_is_the_one_tel_aviv_has_not_seen(self):
        us_days, us_px = walk(7, n=400)
        ta_days = [d for d in us_days if dt.date.fromisoformat(d).weekday() < 4]          # Tel Aviv shut on Fridays here
        ta_px = walk(8, n=len(ta_days))[1]
        assets = {"SPY": lab.Asset("SPY", "fund", us_days, us_px), "^TA125.TA": lab.Asset("^TA125.TA", "fund", ta_days, ta_px)}
        year, gap, ups = lab.lag_rows(assets)
        us = assets["SPY"]
        i = 10                                                                              # a Tel Aviv bar; find it among the rows
        d0, d1 = ta_days[i], ta_days[i + 1]
        a, b = us.dates.index(d0) - 1, us.dates.index(d1) - 1
        self.assertAlmostEqual(gap[i - 1], np.clip(100 * (us.lp[b] - us.lp[a]), -lab.LAG_CLIP, lab.LAG_CLIP))
        thursdays = [j for j in range(1, len(ta_days) - 5) if dt.date.fromisoformat(ta_days[j]).weekday() == 3]
        j = thursdays[3]
        fri = us.dates.index(ta_days[j]) + 1                                                # Thursday's gap runs through Friday's US close
        self.assertAlmostEqual(gap[j - 1], np.clip(100 * (us.lp[fri] - us.lp[fri - 2]), -lab.LAG_CLIP, lab.LAG_CLIP))


if __name__ == "__main__":
    unittest.main(verbosity=1)
