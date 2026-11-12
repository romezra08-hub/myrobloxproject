// Tests for the allocation engine.  Run:  node --test market-compass/app/src/
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const E = require('./engine.js');

const sum = (w) => E.SLEEVES.reduce((a, k) => a + w[k], 0);
const near = (a, b, eps = 1e-9) => assert.ok(Math.abs(a - b) <= eps, `${a} !~ ${b}`);
const HORIZONS = [0, 0.5, 1, 2, 3, 4, 5, 7, 10, 15, 30];
const RISKS = [1, 2, 3, 4, 5];
const CRYPTOS = ['none', 'small', 'medium', 'high'];
const STYLES = ['steady', 'balanced', 'active'];
const NOW = Date.parse('2026-11-12T18:00:00Z');

function scoresOf(v) {
  const o = {};
  E.RISKY.forEach((k) => { o[k] = { final: typeof v === 'number' ? v : v[k] ?? 0 }; });
  return o;
}
function everyProfile(fn) {
  for (const horizon of HORIZONS) for (const risk of RISKS) for (const crypto of CRYPTOS) fn({ horizon, risk, crypto });
}

test('baseline always sums to 100 with no negative parts', () => {
  everyProfile((p) => {
    const b = E.baseAllocation(p);
    near(sum(b.weights), 100, 1e-9);
    E.SLEEVES.forEach((k) => assert.ok(b.weights[k] >= 0, `${k} negative for ${JSON.stringify(p)}`));
  });
});

test('money needed within a year stays entirely in cash', () => {
  for (const risk of RISKS) {
    const b = E.baseAllocation({ horizon: 0.5, risk, crypto: 'high' });
    assert.equal(b.weights.cash, 100);
    assert.equal(b.growth, 0);
  }
});

test('growth assets respect both nerve and horizon', () => {
  assert.equal(E.baseAllocation({ horizon: 30, risk: 5 }).growth, 95);
  assert.equal(E.baseAllocation({ horizon: 30, risk: 1 }).growth, 20);
  const short = E.baseAllocation({ horizon: 2, risk: 5 });
  assert.equal(short.growth, 30);
  assert.equal(short.limitedBy, 'horizon');
  assert.equal(E.baseAllocation({ horizon: 30, risk: 3 }).limitedBy, 'risk');
  // growth share never falls as the horizon lengthens
  for (const risk of RISKS) {
    let prev = -1;
    for (const horizon of HORIZONS) {
      const g = E.baseAllocation({ horizon, risk }).growth;
      assert.ok(g >= prev);
      prev = g;
    }
  }
});

test('crypto never exceeds the chosen cap, and is zero for short horizons', () => {
  everyProfile((p) => {
    const c = E.baseAllocation(p).weights.crypto;
    assert.ok(c <= E.CRYPTO_CAP[p.crypto] + 1e-9);
    if (p.crypto === 'none' || p.horizon < 3) assert.equal(c, 0);
  });
  // a cautious investor asking for "high" still gets only a sliver
  assert.ok(E.baseAllocation({ horizon: 20, risk: 1, crypto: 'high' }).weights.crypto <= 2.5 + 1e-9);
  assert.equal(E.baseAllocation({ horizon: 20, risk: 5, crypto: 'high' }).weights.crypto, 10);
});

test('tilted mix sums to 100, stays non-negative and inside every cap for extreme readings', () => {
  const extremes = [1, -1, 0, { us: 1, intl: -1, crypto: 1, gold: -1, bonds: 1 }, { us: -1, intl: 1, crypto: -1, gold: 1, bonds: -1 }];
  everyProfile((p) => {
    for (const style of STYLES) for (const ex of extremes) {
      const prof = { ...p, style };
      const base = E.baseAllocation(prof);
      const w = E.tilt(base, scoresOf(ex), prof);
      near(sum(w), 100, 1e-9);
      E.SLEEVES.forEach((k) => assert.ok(w[k] >= -1e-9, `${k} negative`));
      assert.ok(w.crypto <= E.CRYPTO_CAP[p.crypto] + 1e-9, 'crypto over cap');
      assert.ok(w.us + w.intl + w.crypto <= E.horizonCap(p.horizon) + 1e-9, 'growth over horizon cap');
      const k = E.STYLE_K[style];
      E.RISKY.forEach((s) => assert.ok(w[s] <= base.weights[s] * (1 + k) + 1e-9, `${s} tilted past its bound`));
    }
  });
});

test('steady style ignores every signal', () => {
  const prof = { horizon: 10, risk: 3, crypto: 'medium', style: 'steady' };
  const base = E.baseAllocation(prof);
  const w = E.tilt(base, scoresOf(-1), prof);
  E.SLEEVES.forEach((k) => near(w[k], base.weights[k], 1e-9));
});

test('a negative reading trims the part and parks the difference in cash', () => {
  const prof = { horizon: 20, risk: 3, crypto: 'none', style: 'balanced' };
  const base = E.baseAllocation(prof);
  const w = E.tilt(base, scoresOf({ gold: -1 }), prof);
  near(w.gold, base.weights.gold * 0.65);
  near(w.cash - base.weights.cash, base.weights.gold * 0.35);
  near(w.us, base.weights.us);
});

test('active style leans twice as far as balanced', () => {
  const mk = (style) => {
    const prof = { horizon: 20, risk: 3, crypto: 'none', style };
    const base = E.baseAllocation(prof);
    return base.weights.bonds - E.tilt(base, scoresOf({ bonds: -0.5 }), prof).bonds;
  };
  near(mk('active'), 2 * mk('balanced'));
});

test('rounding keeps the total at exactly 100', () => {
  everyProfile((p) => {
    for (const style of STYLES) {
      const prof = { ...p, style };
      const r = E.roundWeights(E.tilt(E.baseAllocation(prof), scoresOf({ us: 0.31, intl: 0.03, crypto: -0.17, gold: -0.73, bonds: -0.46 }), prof));
      assert.equal(sum(r), 100);
      E.SLEEVES.forEach((k) => assert.ok(Number.isInteger(r[k]) && r[k] >= 0));
    }
  });
  assert.deepEqual(E.roundWeights({ us: 0, intl: 0, crypto: 0, gold: 0, bonds: 0, cash: 0 }).cash, 100);
});

test('event reading is a fifth of the blend, and only while the brief is fresh', () => {
  const snap = { sleeves: { us: { score: 0.5 }, intl: { score: 0.0 }, crypto: { score: null }, gold: {}, bonds: { score: -1 } } };
  const brief = { generatedAt: '2026-11-12T12:00:00Z', sleeveScores: { us: { score: -1 }, crypto: { score: -1 }, bonds: { score: 1 } } };
  const s = E.blendScores(snap, brief, NOW);
  near(s.us.final, 0.8 * 0.5 + 0.2 * -1);
  near(s.intl.final, 0);                    // no event reading: price reading alone
  near(s.crypto.final, 0.2 * -1);           // no price reading: a fifth of the event reading
  assert.equal(s.gold.final, 0);
  near(s.bonds.final, -0.8 + 0.2);
  const stale = E.blendScores(snap, { ...brief, generatedAt: '2026-11-01T12:00:00Z' }, NOW);
  near(stale.us.final, 0.5);
  assert.equal(stale.us.eventUsed, false);
  assert.equal(E.briefIsFresh(null, NOW), false);
  assert.equal(E.briefIsFresh({ generatedAt: 'nonsense' }, NOW), false);
});

test('readings outside [-1, 1] are clamped before use', () => {
  const s = E.blendScores({ sleeves: { us: { score: 7 } } }, null, NOW);
  assert.equal(s.us.final, 1);
});

test('new money follows the target when nothing is held', () => {
  const target = { us: 40, intl: 20, crypto: 2, gold: 5, bonds: 23, cash: 10 };
  const b = E.buyPlan(target, E.DEFAULTS.holdings, 1000);
  near(b.buys.us, 400);
  near(b.buys.crypto, 20);
  near(sum(b.buys), 1000);
  assert.equal(b.trims.length, 0);
});

test('with holdings, new money goes to what is furthest below target', () => {
  const target = { us: 50, intl: 0, crypto: 0, gold: 0, bonds: 50, cash: 0 };
  // $2,000 after the deposit, so each side should reach $1,000: bonds are $900 short, stocks $100 short
  const b = E.buyPlan(target, { us: 900, intl: 0, crypto: 0, gold: 0, bonds: 100, cash: 0 }, 1000);
  near(b.buys.bonds, 900);
  near(b.buys.us, 100);
  near(sum(b.buys), 1000);
  assert.equal(b.trims.length, 0);          // buying alone lands exactly on target, nothing to trim
  const even = E.buyPlan(target, { us: 500, intl: 0, crypto: 0, gold: 0, bonds: 500, cash: 0 }, 1000);
  near(even.buys.us, 500);
  near(even.buys.bonds, 500);
  // too lopsided for new money to fix: everything goes to bonds and stocks are still flagged
  const heavy = E.buyPlan(target, { us: 5000, intl: 0, crypto: 0, gold: 0, bonds: 0, cash: 0 }, 1000);
  near(heavy.buys.bonds, 1000);
  near(heavy.buys.us, 0);
  assert.equal(heavy.trims[0].key, 'us');
  near(heavy.trims[0].share, 5000 / 6000 * 100);
  near(heavy.trims[0].over, 5000 / 6000 * 100 - 50);
});

test('pacing: lump sum by default, steps when markets are stressed or nerves are thin', () => {
  const target = { us: 40, intl: 20, crypto: 2, gold: 5, bonds: 23, cash: 10 };
  const calm = { regime: { score: 0.3 }, macro: { vix: 16 } };
  const storm = { regime: { score: -0.6 }, macro: { vix: 31 } };
  const P = (o) => E.normalizeProfile(o);
  assert.equal(E.pacing(P({ amount: 10000, risk: 3 }), target, calm).mode, 'now');
  assert.equal(E.pacing(P({ amount: 10000, risk: 3 }), target, storm).steps, 3);
  assert.equal(E.pacing(P({ amount: 10000, risk: 2 }), target, calm).steps, 4);
  assert.equal(E.pacing(P({ amount: 10000, risk: 1 }), target, storm).steps, 6);
  assert.equal(E.pacing(P({ amount: 300, risk: 1 }), target, storm).why, 'small');
  assert.equal(E.pacing(P({ amount: 10000, risk: 3 }), { ...target, cash: 100 }, calm).why, 'cash');
});

test('stress test weights each part by its worst fall', () => {
  const s = E.stressTest({ us: 50, intl: 0, crypto: 0, gold: 0, bonds: 0, cash: 50 });
  near(s.pct, -25.5);
  assert.equal(E.stressTest({ us: 0, intl: 0, crypto: 0, gold: 0, bonds: 0, cash: 100 }).pct, 0);
});

test('profile input is sanitised', () => {
  const p = E.normalizeProfile({ amount: 'abc', horizon: -5, risk: 99, crypto: 'yolo', style: 'x', holdings: { us: -3, bonds: '250' } });
  assert.equal(p.amount, 1000);
  assert.equal(p.horizon, 0);
  assert.equal(p.risk, 5);
  assert.equal(p.crypto, 'small');
  assert.equal(p.style, 'balanced');
  assert.equal(p.holdings.us, 0);
  assert.equal(p.holdings.bonds, 250);
});

test('full plan is coherent and flags what needs attention first', () => {
  const snap = {
    regime: { score: 0.27 }, macro: { vix: 17.5 },
    sleeves: { us: { score: 0.31 }, intl: { score: 0.03 }, crypto: { score: -0.04 }, gold: { score: -0.83 }, bonds: { score: -0.43 } }
  };
  const brief = { generatedAt: '2026-11-12T17:00:00Z', sleeveScores: { us: { score: -0.2 }, bonds: { score: -0.6 }, crypto: { score: -0.7 }, gold: { score: -0.3 }, intl: { score: -0.25 } } };
  const pl = E.plan({ amount: 5000, horizon: 12, risk: 3, crypto: 'medium', style: 'balanced', efund: false, debt: true }, snap, brief, NOW);
  assert.equal(sum(pl.target), 100);
  near(sum(pl.buy.buys), 5000, 1e-6);
  assert.deepEqual(pl.checks.map((c) => c.id), ['debt', 'efund']);
  const row = Object.fromEntries(pl.rows.map((r) => [r.key, r]));
  assert.equal(row.gold.stance, 'under');
  assert.equal(row.bonds.stance, 'under');
  assert.equal(row.cash.stance, 'extra');
  assert.ok(row.us.target >= row.us.base);
  assert.ok(pl.eventsUsed);
  assert.ok(pl.stress.pct < 0);
  // an empty snapshot degrades to the baseline rather than throwing
  const bare = E.plan({ horizon: 12, risk: 3 }, null, null, NOW);
  assert.deepEqual(bare.target, bare.baseRounded);
});

test('risk shares add to one and match a hand-worked two-asset case', () => {
  // 50/50 stocks and cash: cash barely moves, so stocks carry essentially all of the risk
  const half = E.riskShares({ us: 50, intl: 0, crypto: 0, gold: 0, bonds: 0, cash: 50 }, null);
  near(E.SLEEVES.reduce((a, k) => a + half.shares[k], 0), 1, 1e-9);
  assert.ok(half.shares.us > 0.99);
  near(half.vol, Math.sqrt(0.25 * 0.16 * 0.16 + 0.25 * 0.01 * 0.01), 1e-9);
  // two uncorrelated parts with equal swings and equal weights share risk equally
  const live = { vol: { us: 0.2, intl: 0.2, crypto: 0.65, gold: 0.2, bonds: 0.2, cash: 0.01 },
    corr: { us: { intl: 0 }, intl: { us: 0 } } };
  const even = E.riskShares({ us: 50, intl: 50, crypto: 0, gold: 0, bonds: 0, cash: 0 }, live);
  near(even.shares.us, 0.5, 1e-9);
  near(even.vol, Math.sqrt(2 * 0.25 * 0.04), 1e-9);
  assert.equal(even.live, true);
});

test('a small crypto slice carries a far larger share of the risk', () => {
  const r = E.riskShares({ us: 40, intl: 20, crypto: 5, gold: 5, bonds: 25, cash: 5 }, null);
  assert.ok(r.shares.crypto > 0.12, `crypto share ${r.shares.crypto}`);   // 5% of the money, well over 12% of the risk
  assert.ok(r.shares.bonds < 0.05);                                        // 25% of the money, under 5% of the risk
  near(E.SLEEVES.reduce((a, k) => a + r.shares[k], 0), 1, 1e-9);
});

test('a calm recent spell never makes a part look safer than its history', () => {
  const calm = { vol: { us: 0.05, intl: 0.05, crypto: 0.10, gold: 0.05, bonds: 0.01, cash: 0.001 }, corr: {} };
  const r = E.riskShares({ us: 100, intl: 0, crypto: 0, gold: 0, bonds: 0, cash: 0 }, calm);
  near(r.vol, E.LONG_RUN_VOL.us, 1e-9);
  const wild = { vol: { us: 0.40 }, corr: {} };
  near(E.riskShares({ us: 100, intl: 0, crypto: 0, gold: 0, bonds: 0, cash: 0 }, wild).vol, 0.40, 1e-9);
  // all cash: no risk, and no division by zero
  const none = E.riskShares({ us: 0, intl: 0, crypto: 0, gold: 0, bonds: 0, cash: 0 }, null);
  assert.equal(none.vol, 0);
  assert.equal(none.shares.us, 0);
});

test('a part that moves against the rest carries a negative share', () => {
  const hedge = { vol: { us: 0.2, bonds: 0.1 }, corr: { us: { bonds: -0.9 }, bonds: { us: -0.9 } } };
  const r = E.riskShares({ us: 80, intl: 0, crypto: 0, gold: 0, bonds: 20, cash: 0 }, hedge);
  assert.ok(r.shares.bonds < 0);
  near(r.shares.us + r.shares.bonds, 1, 1e-9);
});

test('future value matches the textbook formulas', () => {
  near(E.futureValue(1000, 0, 10, 0.07).value, 1000 * Math.pow(1.07, 10), 1e-6);
  near(E.futureValue(0, 100, 10, 0).value, 12000, 1e-9);
  assert.equal(E.futureValue(0, 100, 10, 0).paidIn, 12000);
  // one year of monthly deposits at 6% a year: an annuity at the matching monthly rate
  const i = Math.pow(1.06, 1 / 12) - 1;
  near(E.futureValue(0, 100, 1, 0.06).value, 100 * (Math.pow(1 + i, 12) - 1) / i, 1e-9);
  // the two pieces simply add
  near(E.futureValue(1000, 100, 5, 0.05).value, E.futureValue(1000, 0, 5, 0.05).value + E.futureValue(0, 100, 5, 0.05).value, 1e-6);
  // bad input degrades to zero rather than NaN
  assert.equal(E.futureValue('x', -5, 'y', 0.05).value, 0);
  // starting ten years earlier roughly doubles the result at 7%
  assert.ok(E.futureValue(0, 100, 40, 0.07).value > 1.9 * E.futureValue(0, 100, 30, 0.07).value);
});

test('fee drag: one percent a year for forty years takes about a third', () => {
  near(E.feeDrag(40, 0.07, 0.01), 1 - Math.pow(1.06 / 1.07, 40), 1e-12);
  assert.ok(E.feeDrag(40, 0.07, 0.01) > 0.30 && E.feeDrag(40, 0.07, 0.01) < 0.33);
  assert.equal(E.feeDrag(40, 0.07, 0), 0);
  assert.ok(E.feeDrag(40, 0.07, 0.0003) < 0.012);     // a 0.03% index fund takes about one percent
});

test('the plan carries risk shares for its target mix', () => {
  const pl = E.plan({ horizon: 20, risk: 4, crypto: 'high' }, null, null, NOW);
  near(E.SLEEVES.reduce((a, k) => a + pl.risk.shares[k], 0), 1, 1e-9);
  assert.ok(pl.risk.shares.crypto > pl.target.crypto / 100);
  assert.ok(pl.risk.vol > 0.1 && pl.risk.vol < 0.3);
});
