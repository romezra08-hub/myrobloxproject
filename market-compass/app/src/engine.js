/* Market Compass allocation engine.
 *
 * Pure functions: a personal profile + the live snapshot + the news brief in,
 * a plan out. No DOM, no network, no clock (the caller passes `now`), so the
 * same file runs in the page and under `node --test`.
 *
 * The method, in one paragraph: your time horizon and nerve set a diversified
 * baseline (that decision matters far more than any forecast). Live trend,
 * valuation, liquidity and event readings may then lean each part up or down
 * by a bounded amount, with anything trimmed parked in T-bills. Hard caps keep
 * the tilts from ever overriding the baseline's risk limits.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.MCEngine = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // Display and stacking order: growth assets first, then the stabilisers.
  var SLEEVES = ['us', 'intl', 'crypto', 'gold', 'bonds', 'cash'];
  var RISKY = ['us', 'intl', 'crypto', 'gold', 'bonds'];
  var LABELS = {
    us: 'US stocks', intl: 'International stocks', crypto: 'Crypto',
    gold: 'Gold', bonds: 'Bonds', cash: 'Cash and T-bills'
  };

  // Share of the plan in growth assets (stocks + crypto) by nerve, before the horizon cap.
  var RISK_GROWTH = { 1: 20, 2: 40, 3: 60, 4: 80, 5: 95 };
  var RISK_NAMES = { 1: 'Very cautious', 2: 'Cautious', 3: 'Balanced', 4: 'Growth', 5: 'Aggressive' };
  // The most crypto the plan will ever hold, by the choice you make.
  var CRYPTO_CAP = { none: 0, small: 2, medium: 5, high: 10 };
  // How far live signals may move a part away from its baseline (fraction of the part).
  var STYLE_K = { steady: 0, balanced: 0.35, active: 0.7 };
  // Worst peak-to-trough falls since 2000, used for the stress test (percent).
  var WORST = { us: -51, intl: -57, crypto: -80, gold: -45, bonds: -17, cash: 0 };
  var BRIEF_MAX_AGE_H = 96;     // an event read older than four days no longer moves the plan
  var EVENT_WEIGHT = 0.2;       // events are a fifth of each part's reading; prices are the rest

  var DEFAULTS = {
    amount: 1000, horizon: 10, risk: 3, crypto: 'small', style: 'balanced',
    efund: true, debt: false,
    holdings: { us: 0, intl: 0, crypto: 0, gold: 0, bonds: 0, cash: 0 }
  };

  function num(x, d) { x = Number(x); return isFinite(x) ? x : d; }
  function clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }

  function normalizeProfile(p) {
    p = p || {};
    var h = p.holdings || {};
    var out = {
      amount: clamp(num(p.amount, DEFAULTS.amount), 0, 1e9),
      horizon: clamp(num(p.horizon, DEFAULTS.horizon), 0, 60),
      risk: clamp(Math.round(num(p.risk, DEFAULTS.risk)), 1, 5),
      crypto: CRYPTO_CAP.hasOwnProperty(p.crypto) ? p.crypto : DEFAULTS.crypto,
      style: STYLE_K.hasOwnProperty(p.style) ? p.style : DEFAULTS.style,
      efund: p.efund === undefined ? DEFAULTS.efund : !!p.efund,
      debt: !!p.debt,
      holdings: {}
    };
    SLEEVES.forEach(function (k) { out.holdings[k] = clamp(num(h[k], 0), 0, 1e9); });
    return out;
  }

  /** The most that may sit in growth assets for money needed in `years`. */
  function horizonCap(years) {
    if (years < 1) return 0;
    if (years < 2) return 15;
    if (years < 3) return 30;
    if (years < 5) return 50;
    if (years < 7) return 65;
    if (years < 10) return 80;
    if (years < 15) return 90;
    return 100;
  }

  /** The baseline mix: what you would hold if you ignored every headline. Sums to 100. */
  function baseAllocation(profile) {
    var p = normalizeProfile(profile);
    var cap = horizonCap(p.horizon);
    var want = RISK_GROWTH[p.risk];
    var growth = Math.min(want, cap);

    var crypto = Math.min(CRYPTO_CAP[p.crypto], 0.125 * growth);
    if (p.horizon < 3) crypto = 0;            // too volatile for money needed soon
    else if (p.horizon < 5) crypto = crypto / 2;

    var stocks = growth - crypto;
    var gold = growth <= 0 ? 0 : (growth >= 40 ? 5 : 3);
    var defensive = 100 - growth - gold;
    var cashShare = p.horizon < 1 ? 1 : p.horizon < 3 ? 0.7 : p.horizon < 5 ? 0.4 : 0.2;

    var w = {
      us: stocks * 0.65, intl: stocks * 0.35, crypto: crypto, gold: gold,
      bonds: defensive * (1 - cashShare), cash: defensive * cashShare
    };
    return { weights: w, growth: growth, growthWanted: want, growthCap: cap, limitedBy: cap < want ? 'horizon' : 'risk' };
  }

  /** Is the news brief recent enough to count? */
  function briefIsFresh(brief, now) {
    if (!brief || !brief.generatedAt) return false;
    var t = Date.parse(brief.generatedAt);
    if (!isFinite(t)) return false;
    var ageH = (now - t) / 3.6e6;
    return ageH >= -1 && ageH <= BRIEF_MAX_AGE_H;
  }

  /** Blend each part's price-based reading with the event reading. All in [-1, 1]. */
  function blendScores(snapshot, brief, now) {
    var fresh = briefIsFresh(brief, now);
    var out = {};
    RISKY.forEach(function (k) {
      var sl = snapshot && snapshot.sleeves && snapshot.sleeves[k];
      var s = sl && typeof sl.score === 'number' ? clamp(sl.score, -1, 1) : null;
      var ev = fresh && brief.sleeveScores && brief.sleeveScores[k];
      var e = ev && typeof ev.score === 'number' ? clamp(ev.score, -1, 1) : null;
      var f;
      if (s === null && e === null) f = 0;
      else if (e === null) f = s;
      else if (s === null) f = EVENT_WEIGHT * e;
      else f = (1 - EVENT_WEIGHT) * s + EVENT_WEIGHT * e;
      out[k] = { signal: s, event: e, final: f, eventUsed: e !== null };
    });
    return out;
  }

  /** Lean the baseline by the readings, then enforce the caps. Sums to 100. */
  function tilt(base, scores, profile) {
    var p = normalizeProfile(profile);
    var k = STYLE_K[p.style];
    var w = {};
    RISKY.forEach(function (s) {
      var f = scores && scores[s] ? scores[s].final : 0;
      w[s] = base.weights[s] * (1 + k * clamp(f, -1, 1));
    });
    // 1. never more crypto than you chose
    w.crypto = Math.min(w.crypto, CRYPTO_CAP[p.crypto]);
    // 2. never more growth assets than your horizon allows
    var growth = w.us + w.intl + w.crypto;
    var cap = horizonCap(p.horizon);
    if (growth > cap && growth > 0) {
      var g = cap / growth;
      w.us *= g; w.intl *= g; w.crypto *= g;
    }
    // 3. never more than everything
    var risky = RISKY.reduce(function (a, s) { return a + w[s]; }, 0);
    if (risky > 100) {
      RISKY.forEach(function (s) { w[s] *= 100 / risky; });
      risky = 100;
    }
    w.cash = 100 - risky;
    return w;
  }

  /** Round to whole percents that still add up to exactly 100 (largest remainder). */
  function roundWeights(w) {
    var keys = SLEEVES.slice();
    var total = keys.reduce(function (a, k) { return a + (w[k] || 0); }, 0);
    var out = {};
    if (total <= 0) { keys.forEach(function (k) { out[k] = 0; }); out.cash = 100; return out; }
    var parts = keys.map(function (k) {
      var x = (w[k] || 0) * 100 / total;
      return { k: k, floor: Math.floor(x + 1e-9), rem: x - Math.floor(x + 1e-9) };
    });
    var left = 100 - parts.reduce(function (a, p) { return a + p.floor; }, 0);
    parts.slice().sort(function (a, b) { return b.rem - a.rem || keys.indexOf(a.k) - keys.indexOf(b.k); })
      .forEach(function (p, i) { if (i < left) p.floor += 1; });
    parts.forEach(function (p) { out[p.k] = p.floor; });
    return out;
  }

  function stanceFor(key, base, target) {
    var d = target - base;
    if (key === 'cash') return d >= 1.5 ? 'extra' : d <= -1.5 ? 'less' : 'base';
    if (base < 0.5 && target < 0.5) return 'none';
    if (d >= Math.max(1, 0.075 * base)) return 'over';
    if (d <= -Math.max(1, 0.075 * base)) return 'under';
    return 'base';
  }
  var STANCE_TEXT = {
    over: 'Above baseline', under: 'Below baseline', base: 'At baseline',
    none: 'Not in your mix', extra: 'Holding extra', less: 'Drawn down'
  };

  /**
   * Split new money across the parts.
   * With no holdings, it simply follows the target. With holdings, new money
   * goes to whatever is furthest below target first, so you rebalance by buying
   * rather than selling (no tax bill, no trading costs).
   */
  function buyPlan(target, holdings, amount) {
    var held = SLEEVES.reduce(function (a, k) { return a + (holdings[k] || 0); }, 0);
    var buys = {}, trims = [];
    if (held <= 0) {
      SLEEVES.forEach(function (k) { buys[k] = amount * target[k] / 100; });
      return { buys: buys, trims: trims, held: 0, total: amount };
    }
    var total = held + amount;
    var gaps = {}, pos = 0;
    SLEEVES.forEach(function (k) {
      gaps[k] = total * target[k] / 100 - (holdings[k] || 0);
      if (gaps[k] > 0) pos += gaps[k];
    });
    SLEEVES.forEach(function (k) { buys[k] = pos > 0 && gaps[k] > 0 ? amount * gaps[k] / pos : 0; });
    // What is still well over target once the new money is in: buying alone could not fix these.
    SLEEVES.forEach(function (k) {
      var share = total > 0 ? ((holdings[k] || 0) + buys[k]) / total * 100 : 0;
      if (share - target[k] >= 5) trims.push({ key: k, share: share, target: target[k], over: share - target[k] });
    });
    trims.sort(function (a, b) { return b.over - a.over; });
    return { buys: buys, trims: trims, held: held, total: total };
  }

  /** How to put the money in: one go, or in steps. */
  function pacing(p, target, snapshot) {
    var regime = snapshot && snapshot.regime && typeof snapshot.regime.score === 'number' ? snapshot.regime.score : null;
    var vix = snapshot && snapshot.macro ? snapshot.macro.vix : null;
    var atRisk = p.amount * (100 - target.cash) / 100;
    var stressed = (regime !== null && regime < -0.35) || (typeof vix === 'number' && vix >= 26);
    var nervous = p.risk <= 2;
    if (atRisk <= 0) return { mode: 'now', steps: 1, why: 'cash' };
    if (atRisk < 500) return { mode: 'now', steps: 1, why: 'small' };
    if (stressed && nervous) return { mode: 'steps', steps: 6, why: 'stressed-nervous' };
    if (stressed) return { mode: 'steps', steps: 3, why: 'stressed' };
    if (nervous) return { mode: 'steps', steps: 4, why: 'nervous' };
    return { mode: 'now', steps: 1, why: 'evidence' };
  }

  /** What the mix would lose if every part repeated its worst fall since 2000 at once. */
  function stressTest(target) {
    var loss = SLEEVES.reduce(function (a, k) { return a + target[k] * WORST[k] / 100; }, 0);
    return { pct: loss, worst: WORST };
  }

  /** Everything the page shows for one person at one moment. */
  function plan(profile, snapshot, brief, now) {
    var p = normalizeProfile(profile);
    now = typeof now === 'number' ? now : Date.now();
    var base = baseAllocation(p);
    var scores = blendScores(snapshot, brief, now);
    var exact = tilt(base, scores, p);
    var baseR = roundWeights(base.weights);
    var target = roundWeights(exact);
    var buy = buyPlan(target, p.holdings, p.amount);

    var rows = SLEEVES.map(function (k) {
      var st = stanceFor(k, baseR[k], target[k]);
      var sc = scores[k] || null;
      return {
        key: k, label: LABELS[k], base: baseR[k], target: target[k], tilt: target[k] - baseR[k],
        stance: st, stanceText: STANCE_TEXT[st], amount: buy.buys[k],
        signal: sc ? sc.signal : null, event: sc ? sc.event : null, score: sc ? sc.final : null
      };
    });

    var checks = [];
    if (p.debt) checks.push({ id: 'debt', level: 'stop' });
    if (!p.efund) checks.push({ id: 'efund', level: 'stop' });
    if (p.horizon < 1) checks.push({ id: 'short', level: 'note' });
    else if (base.limitedBy === 'horizon') checks.push({ id: 'horizon', level: 'note' });
    if (p.crypto === 'high' && target.crypto > 0) checks.push({ id: 'crypto', level: 'warn' });

    return {
      profile: p, base: base, baseRounded: baseR, target: target, rows: rows,
      scores: scores, buy: buy, pacing: pacing(p, target, snapshot), stress: stressTest(target),
      checks: checks, style: p.style, k: STYLE_K[p.style],
      eventsUsed: briefIsFresh(brief, now), riskName: RISK_NAMES[p.risk]
    };
  }

  return {
    SLEEVES: SLEEVES, RISKY: RISKY, LABELS: LABELS, DEFAULTS: DEFAULTS, RISK_GROWTH: RISK_GROWTH,
    RISK_NAMES: RISK_NAMES, CRYPTO_CAP: CRYPTO_CAP, STYLE_K: STYLE_K, WORST: WORST,
    EVENT_WEIGHT: EVENT_WEIGHT, BRIEF_MAX_AGE_H: BRIEF_MAX_AGE_H, STANCE_TEXT: STANCE_TEXT,
    normalizeProfile: normalizeProfile, horizonCap: horizonCap, baseAllocation: baseAllocation,
    briefIsFresh: briefIsFresh, blendScores: blendScores, tilt: tilt, roundWeights: roundWeights,
    stanceFor: stanceFor, buyPlan: buyPlan, pacing: pacing, stressTest: stressTest, plan: plan
  };
});
