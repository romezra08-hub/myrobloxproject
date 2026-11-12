/* Market Compass allocation engine.
 *
 * Pure functions: a personal profile + the live snapshot + the news brief in,
 * a plan out. No DOM, no network, no clock (the caller passes `now`), so the
 * same file runs in the page and under `node --test`.
 *
 * The method, in one paragraph: your time horizon and nerve set a diversified
 * baseline, and that decision matters far more than any forecast. Live trend,
 * valuation and risk readings may then lean each part by a small, bounded
 * amount, with anything trimmed parked in T-bills. News can only make the plan
 * more careful, never bolder. Hard caps keep the leans from overriding the
 * baseline's risk limits. Every number below is tied to a source in the
 * page's Library and Method tabs.
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
  // The top is 90, not 100: long horizons do not make stocks safe, and US history is the lucky draw.
  var RISK_GROWTH = { 1: 20, 2: 40, 3: 60, 4: 80, 5: 90 };
  var RISK_NAMES = { 1: 'Very cautious', 2: 'Cautious', 3: 'Balanced', 4: 'Growth', 5: 'Aggressive' };
  // The most crypto the plan will ever hold, by the choice you make.
  var CRYPTO_CAP = { none: 0, small: 2, medium: 5, high: 10 };
  // How far a full reading may move a part away from its baseline, as a fraction of the part.
  // Trimming is allowed further than adding: the evidence for trend rules is that they
  // reduce losses, not that they raise returns.
  var STYLE = {
    steady: { down: 0, up: 0 },
    balanced: { down: 0.35, up: 0.20 },
    active: { down: 0.50, up: 0.25 }
  };
  // Deepest month-end falls since 2000 (percent). Older history was worse; see SCENARIOS.
  var WORST = { us: -51, intl: -57, crypto: -85, gold: -45, bonds: -17, cash: 0 };
  // Real episodes, part by part (percent, approximate). Crypto did not exist in 2008,
  // so its own typical bear-market fall is assumed there.
  var SCENARIOS = [
    { id: 'crisis', r: { us: -51, intl: -57, crypto: -80, gold: 20, bonds: 6, cash: 2 } },
    { id: 'inflation', r: { us: -19, intl: -16, crypto: -64, gold: 0, bonds: -13, cash: 1.5 } },
    { id: 'worst', r: WORST }
  ];
  // Long-run yearly swings (standard deviation). Recent calm is never allowed to
  // make a part look safer than its history: the higher of live and long-run is used.
  var LONG_RUN_VOL = { us: 0.16, intl: 0.17, crypto: 0.65, gold: 0.16, bonds: 0.06, cash: 0.01 };
  // How the parts have tended to move together, used only when no live reading exists.
  var LONG_RUN_CORR = {
    us:     { us: 1, intl: 0.85, crypto: 0.35, gold: 0.05, bonds: 0.10, cash: 0 },
    intl:   { us: 0.85, intl: 1, crypto: 0.30, gold: 0.15, bonds: 0.15, cash: 0 },
    crypto: { us: 0.35, intl: 0.30, crypto: 1, gold: 0.10, bonds: 0.05, cash: 0 },
    gold:   { us: 0.05, intl: 0.15, crypto: 0.10, gold: 1, bonds: 0.25, cash: 0 },
    bonds:  { us: 0.10, intl: 0.15, crypto: 0.05, gold: 0.25, bonds: 1, cash: 0 },
    cash:   { us: 0, intl: 0, crypto: 0, gold: 0, bonds: 0, cash: 1 }
  };
  var INFLATION_ASSUMED = 2.5;  // percent a year, used to turn today's yields into after-inflation returns
  var BRIEF_MAX_AGE_H = 96;     // an event read older than four days no longer moves the plan
  var EVENT_WEIGHT = 0.1;       // news is a tenth of a reading at most, and only in the careful direction

  var DEFAULTS = {
    amount: 1000, monthly: 0, horizon: 10, risk: 3, crypto: 'small', style: 'balanced',
    efund: true, debt: false, unstable: false,
    holdings: { us: 0, intl: 0, crypto: 0, gold: 0, bonds: 0, cash: 0 }
  };

  function num(x, d) { x = Number(x); return isFinite(x) ? x : d; }
  function clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }
  function isNum(x) { return typeof x === 'number' && isFinite(x); }

  function normalizeProfile(p) {
    p = p || {};
    var h = p.holdings || {};
    var out = {
      amount: clamp(num(p.amount, DEFAULTS.amount), 0, 1e9),
      monthly: clamp(num(p.monthly, DEFAULTS.monthly), 0, 1e7),
      horizon: clamp(num(p.horizon, DEFAULTS.horizon), 0, 60),
      risk: clamp(Math.round(num(p.risk, DEFAULTS.risk)), 1, 5),
      crypto: CRYPTO_CAP.hasOwnProperty(p.crypto) ? p.crypto : DEFAULTS.crypto,
      style: STYLE.hasOwnProperty(p.style) ? p.style : DEFAULTS.style,
      efund: p.efund === undefined ? DEFAULTS.efund : !!p.efund,
      debt: !!p.debt,
      unstable: !!p.unstable,
      holdings: {}
    };
    SLEEVES.forEach(function (k) { out.holdings[k] = clamp(num(h[k], 0), 0, 1e9); });
    return out;
  }

  /**
   * The most that may sit in growth assets for money needed in `years`.
   * The test behind each rung: if stocks halved, as they did in 2000-02 and 2007-09,
   * the loss must be one the goal survives in the time left.
   */
  function horizonCap(years) {
    if (years < 1) return 0;
    if (years < 2) return 10;
    if (years < 3) return 20;
    if (years < 5) return 35;
    if (years < 7) return 50;
    if (years < 10) return 70;
    if (years < 15) return 85;
    return 90;
  }

  /** The baseline mix: what you would hold if you ignored every headline. Sums to 100. */
  function baseAllocation(profile) {
    var p = normalizeProfile(profile);
    var cap = horizonCap(p.horizon);
    var want = RISK_GROWTH[p.risk];
    if (p.unstable) want = Math.max(0, want - 10);   // a shaky pay cheque is already a risky asset
    var growth = Math.min(want, cap);

    // Crypto is sized by risk, not by enthusiasm: at most a tenth of the growth share,
    // none for the most cautious answer, and none for money needed inside a full crypto cycle.
    var crypto = Math.min(CRYPTO_CAP[p.crypto], growth / 10);
    if (p.risk === 1) crypto = 0;
    else if (p.risk === 2) crypto = crypto / 2;
    if (p.horizon < 4) crypto = 0;
    else if (p.horizon < 6) crypto = crypto / 2;

    var stocks = growth - crypto;
    var gold = (growth <= 0 || p.horizon < 3) ? 0 : (growth >= 40 ? 5 : 3);
    var defensive = 100 - growth - gold;
    var cashShare = p.horizon < 1 ? 1 : p.horizon < 3 ? 0.7 : p.horizon < 5 ? 0.4 : 0.2;
    var cash = defensive * cashShare;
    if (p.horizon >= 10) cash = Math.min(cash, 5);  // over decades cash barely beats inflation

    var w = {
      us: stocks * 0.65, intl: stocks * 0.35, crypto: crypto, gold: gold,
      bonds: defensive - cash, cash: cash
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

  /**
   * Combine each part's price-based reading with the news reading. All in [-1, 1].
   * News may only make the plan more careful. It is ignored when it is rosier than
   * the price reading, it counts for a tenth when it is gloomier, and it can shrink a
   * positive lean to nothing but never turn it negative. Acting on headlines is the
   * least supported input in the research, so it gets the least room.
   */
  function blendScores(snapshot, brief, now) {
    var fresh = briefIsFresh(brief, now);
    var out = {};
    RISKY.forEach(function (k) {
      var sl = snapshot && snapshot.sleeves && snapshot.sleeves[k];
      var s = sl && isNum(sl.score) ? clamp(sl.score, -1, 1) : null;
      var ev = fresh && brief.sleeveScores && brief.sleeveScores[k];
      var e = ev && isNum(ev.score) ? clamp(ev.score, -1, 1) : null;
      var f;
      if (s === null) f = e !== null && e < 0 ? EVENT_WEIGHT * e : 0;
      else if (e === null || e >= s) f = s;
      else {
        f = (1 - EVENT_WEIGHT) * s + EVENT_WEIGHT * e;
        if (s > 0 && f < 0) f = 0;
      }
      out[k] = { signal: s, event: e, final: f, eventUsed: e !== null && f !== (s === null ? 0 : s), eventEffect: f - (s === null ? 0 : s) };
    });
    return out;
  }

  /** Lean the baseline by the readings, then enforce the caps. Sums to 100. */
  function tilt(base, scores, profile) {
    var p = normalizeProfile(profile);
    var lean = STYLE[p.style];
    var w = {};
    RISKY.forEach(function (s) {
      var f = clamp(scores && scores[s] ? scores[s].final : 0, -1, 1);
      w[s] = base.weights[s] * (1 + (f >= 0 ? lean.up : lean.down) * f);
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
   * How far a holding may drift before it is worth trading: 5 points, or a quarter
   * of its target if that is less, and never under 1 point. Inside the band, leave it.
   * Rebalancing controls risk rather than adding return, and the exact rule matters
   * little, so the aim is one or two trades a year.
   */
  function driftBand(target) { return Math.max(1, Math.min(5, 0.25 * target)); }

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
    // What is still outside its band once the new money is in: buying alone could not fix these.
    SLEEVES.forEach(function (k) {
      var share = total > 0 ? ((holdings[k] || 0) + buys[k]) / total * 100 : 0;
      if (share - target[k] >= driftBand(target[k])) trims.push({ key: k, share: share, target: target[k], over: share - target[k] });
    });
    trims.sort(function (a, b) { return b.over - a.over; });
    return { buys: buys, trims: trims, held: held, total: total };
  }

  /**
   * How to put the money in. A lump sum has beaten spreading out about two times in
   * three, so it is the default. Stepping in is offered only to people who said a fall
   * would shake them, as a fixed schedule decided in advance. Market conditions play
   * no part: waiting for calm is market timing.
   */
  function pacing(p, target) {
    var atRisk = p.amount * (100 - target.cash) / 100;
    if (atRisk <= 0) return { mode: 'now', steps: 1, why: 'cash' };
    if (atRisk < 500) return { mode: 'now', steps: 1, why: 'small' };
    if (p.risk === 1) return { mode: 'steps', steps: 6, why: 'nervous' };
    if (p.risk === 2) return { mode: 'steps', steps: 3, why: 'nervous' };
    return { mode: 'now', steps: 1, why: 'evidence' };
  }

  /** What the mix would do in each scenario, and the gain then needed to get back to even. */
  function stressTest(target) {
    var list = SCENARIOS.map(function (sc) {
      var pct = SLEEVES.reduce(function (a, k) { return a + target[k] * sc.r[k] / 100; }, 0);
      var loss = Math.min(0.99, Math.max(0, -pct / 100));
      return { id: sc.id, pct: pct, recover: loss > 0 ? loss / (1 - loss) * 100 : 0, parts: sc.r };
    });
    return { pct: list[list.length - 1].pct, scenarios: list, worst: WORST };
  }

  /**
   * How much of the mix's risk each part carries.
   * Portfolio variance is the sum over every pair of weight x weight x swing x swing x correlation;
   * a part's share is its own row of that sum. Shares add to 1. A part that tends to move
   * against the rest can carry a negative share, which means it is lowering total risk.
   */
  function riskShares(weights, risk) {
    var live = !!(risk && risk.vol && risk.corr);
    var vol = {};
    SLEEVES.forEach(function (k) {
      var v = live && isNum(risk.vol[k]) ? risk.vol[k] : 0;
      vol[k] = Math.max(v, LONG_RUN_VOL[k]);
    });
    function corr(a, b) {
      if (a === b) return 1;
      var c = live && risk.corr[a] ? risk.corr[a][b] : null;
      return isNum(c) ? clamp(c, -1, 1) : LONG_RUN_CORR[a][b];
    }
    var rows = {}, variance = 0;
    SLEEVES.forEach(function (a) {
      var row = 0;
      SLEEVES.forEach(function (b) { row += (weights[b] || 0) / 100 * vol[a] * vol[b] * corr(a, b); });
      rows[a] = (weights[a] || 0) / 100 * row;
      variance += rows[a];
    });
    var shares = {};
    SLEEVES.forEach(function (k) { shares[k] = variance > 0 ? rows[k] / variance : 0; });
    return { vol: Math.sqrt(Math.max(0, variance)), shares: shares, vols: vol, live: live };
  }

  /**
   * What a starting sum plus a steady monthly deposit grows to at a yearly rate.
   * Deposits land at the end of each month and compound monthly at the rate that
   * matches the yearly one, so twelve months at 6% is exactly 6%.
   */
  function futureValue(start, monthly, years, rate) {
    start = Math.max(0, num(start, 0)); monthly = Math.max(0, num(monthly, 0));
    years = Math.max(0, num(years, 0)); rate = num(rate, 0);
    var months = Math.round(years * 12);
    var i = Math.pow(1 + rate, 1 / 12) - 1;
    var grown = start * Math.pow(1 + i, months);
    var stream = Math.abs(i) < 1e-12 ? monthly * months : monthly * (Math.pow(1 + i, months) - 1) / i;
    return { value: grown + stream, paidIn: start + monthly * months, months: months };
  }

  /** Share of final wealth a yearly fee takes: 1 - ((1 + r - fee) / (1 + r)) ^ years, for a single sum. */
  function feeDrag(years, rate, fee) {
    years = Math.max(0, num(years, 0));
    return 1 - Math.pow((1 + rate - fee) / (1 + rate), years);
  }

  /**
   * What each part can reasonably be expected to earn a year after inflation, in percent.
   * Built from today's starting points rather than from past returns:
   *   stocks  the earnings yield on ten-year average profits (100 / Shiller P/E)
   *   bonds   today's yield less assumed inflation; starting yield is the best forecast there is
   *   cash    today's bill yield less inflation for a few years, fading to its long-run 0.5%
   *   gold    about 1%, its record since 1900
   *   crypto  0%: it has no earnings or interest to build a forecast on, so the plan counts on nothing
   * International stocks have no live valuation feed, so they use 4.5%, close to their long-run record.
   */
  function expectedReal(snapshot, years) {
    var m = (snapshot && snapshot.macro) || {};
    var fade = clamp(3 / Math.max(1, num(years, 10)), 0, 1);
    var cashNow = isNum(m.y3m) ? m.y3m - INFLATION_ASSUMED : 0.5;
    return {
      us: isNum(m.cape) && m.cape > 0 ? clamp(100 / m.cape, 1.5, 7) : 3.5,
      intl: 4.5,
      crypto: 0,
      gold: 1,
      bonds: isNum(m.y5y) ? clamp(m.y5y - INFLATION_ASSUMED, -1, 5) : 2,
      cash: clamp(fade * cashNow + (1 - fade) * 0.5, -1, 3),
      live: isNum(m.cape) && isNum(m.y5y)
    };
  }

  /**
   * A range for where the money could end up, in today's dollars.
   * The middle uses expectedReal. The range is one standard error of the yearly average
   * either side (swing / square root of years), which history suggests holds about two
   * times in three. It is a rough guide, not a promise: the worst outcomes lie outside it.
   */
  function outlook(target, snapshot, profile, riskVol) {
    var p = normalizeProfile(profile);
    var exp = expectedReal(snapshot, p.horizon);
    var mid = SLEEVES.reduce(function (a, k) { return a + target[k] * exp[k] / 100; }, 0);
    var years = Math.max(1, p.horizon);
    var spread = (isNum(riskVol) ? riskVol : 0.1) * 100 / Math.sqrt(years);
    var held = SLEEVES.reduce(function (a, k) { return a + p.holdings[k]; }, 0);
    var start = held + p.amount;
    function fv(rate) { return futureValue(start, p.monthly, p.horizon, rate / 100).value; }
    return {
      parts: exp, mid: mid, low: mid - spread, high: mid + spread, spread: spread,
      start: start, monthly: p.monthly, years: p.horizon,
      paidIn: futureValue(start, p.monthly, p.horizon, 0).paidIn,
      value: { low: fv(mid - spread), mid: fv(mid), high: fv(mid + spread) },
      feeDrag: feeDrag(p.horizon, (mid + INFLATION_ASSUMED) / 100, 0.01),
      inflation: INFLATION_ASSUMED
    };
  }

  /** The same plan folded into three funds, for anyone who wants fewer moving parts. */
  function threeFund(target) {
    var stocks = target.us + target.intl + target.crypto;
    var us = Math.round(stocks * 0.65);
    return { us: us, intl: stocks - us, bonds: 100 - stocks, stocks: stocks };
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
    var risk = riskShares(target, snapshot && snapshot.risk);

    var rows = SLEEVES.map(function (k) {
      var st = stanceFor(k, baseR[k], target[k]);
      var sc = scores[k] || null;
      return {
        key: k, label: LABELS[k], base: baseR[k], target: target[k], tilt: target[k] - baseR[k],
        stance: st, stanceText: STANCE_TEXT[st], amount: buy.buys[k], riskShare: risk.shares[k],
        signal: sc ? sc.signal : null, event: sc ? sc.event : null, score: sc ? sc.final : null,
        eventEffect: sc ? sc.eventEffect : 0
      };
    });

    var checks = [];
    if (p.debt) checks.push({ id: 'debt', level: 'stop' });
    if (!p.efund) checks.push({ id: 'efund', level: 'stop' });
    if (p.horizon < 1) checks.push({ id: 'short', level: 'note' });
    else if (base.limitedBy === 'horizon') checks.push({ id: 'horizon', level: 'note' });
    if (risk.shares.crypto >= 0.20) checks.push({ id: 'crypto', level: 'warn' });   // a fifth of all the risk in one small slice

    return {
      profile: p, base: base, baseRounded: baseR, target: target, rows: rows,
      scores: scores, buy: buy, pacing: pacing(p, target), stress: stressTest(target),
      risk: risk, outlook: outlook(target, snapshot, p, risk.vol), simple: threeFund(target),
      checks: checks, style: p.style, lean: STYLE[p.style],
      eventsUsed: briefIsFresh(brief, now), riskName: RISK_NAMES[p.risk]
    };
  }

  return {
    SLEEVES: SLEEVES, RISKY: RISKY, LABELS: LABELS, DEFAULTS: DEFAULTS, RISK_GROWTH: RISK_GROWTH,
    RISK_NAMES: RISK_NAMES, CRYPTO_CAP: CRYPTO_CAP, STYLE: STYLE, WORST: WORST, SCENARIOS: SCENARIOS,
    EVENT_WEIGHT: EVENT_WEIGHT, BRIEF_MAX_AGE_H: BRIEF_MAX_AGE_H, STANCE_TEXT: STANCE_TEXT,
    LONG_RUN_VOL: LONG_RUN_VOL, LONG_RUN_CORR: LONG_RUN_CORR, INFLATION_ASSUMED: INFLATION_ASSUMED,
    normalizeProfile: normalizeProfile, horizonCap: horizonCap, baseAllocation: baseAllocation,
    briefIsFresh: briefIsFresh, blendScores: blendScores, tilt: tilt, roundWeights: roundWeights,
    stanceFor: stanceFor, driftBand: driftBand, buyPlan: buyPlan, pacing: pacing, stressTest: stressTest,
    riskShares: riskShares, futureValue: futureValue, feeDrag: feeDrag, expectedReal: expectedReal,
    outlook: outlook, threeFund: threeFund, plan: plan
  };
});
