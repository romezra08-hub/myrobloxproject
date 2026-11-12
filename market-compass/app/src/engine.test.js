// Tests for the allocation engine.  Run:  node --test market-compass/app/src/engine.test.js
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const E = require('./engine.js');

const sum = (w) => E.SLEEVES.reduce((a, k) => a + w[k], 0);
const near = (a, b, eps = 1e-9) => assert.ok(Math.abs(a - b) <= eps, `${a} !~ ${b}`);
const HORIZONS = [0, 0.5, 1, 2, 3, 4, 5, 6, 7, 10, 15, 30];
const RISKS = [1, 2, 3, 4, 5];
const CRYPTOS = ['none', 'small', 'medium', 'high'];
const STYLES = ['steady', 'balanced', 'active'];
const NOW = Date.parse('2026-11-12T18:00:00Z');
const ZERO = { us: 0, intl: 0, crypto: 0, gold: 0, bonds: 0, cash: 0 };

function scoresOf(v) {
  const o = {};
  E.RISKY.forEach((k) => { o[k] = { final: typeof v === 'number' ? v : v[k] ?? 0 }; });
  return o;
}
function everyProfile(fn) {
  for (const horizon of HORIZONS) for (const risk of RISKS) for (const crypto of CRYPTOS) for (const unstable of [false, true]) fn({ horizon, risk, crypto, unstable });
}

// ------------------------------------------------------------------ baseline

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

test('growth assets top out at 90 and follow the horizon ladder', () => {
  assert.equal(E.baseAllocation({ horizon: 40, risk: 5 }).growth, 90);
  assert.equal(E.baseAllocation({ horizon: 40, risk: 1 }).growth, 20);
  assert.deepEqual([0.5, 1, 2, 3, 5, 7, 10, 15].map(E.horizonCap), [0, 10, 20, 35, 50, 70, 85, 90]);
  const short = E.baseAllocation({ horizon: 4, risk: 5 });
  assert.equal(short.growth, 35);
  assert.equal(short.limitedBy, 'horizon');
  assert.equal(E.baseAllocation({ horizon: 30, risk: 3 }).limitedBy, 'risk');
  for (const risk of RISKS) {
    let prev = -1;
    for (const horizon of HORIZONS) {
      const g = E.baseAllocation({ horizon, risk }).growth;
      assert.ok(g >= prev, 'growth share never falls as the horizon lengthens');
      prev = g;
    }
  }
  // the test behind the ladder: a halving of stocks costs at most half the cap
  everyProfile((p) => assert.ok(E.baseAllocation(p).growth <= 90));
});

test('unstable income takes ten points off the growth share', () => {
  assert.equal(E.baseAllocation({ horizon: 30, risk: 4, unstable: true }).growth, 70);
  assert.equal(E.baseAllocation({ horizon: 30, risk: 1, unstable: true }).growth, 10);
  // when the horizon is already the binding limit, it stays the limit
  assert.equal(E.baseAllocation({ horizon: 4, risk: 5, unstable: true }).growth, 35);
});

test('crypto is sized by risk: capped, a tenth of growth at most, and absent where it does not belong', () => {
  everyProfile((p) => {
    const b = E.baseAllocation(p);
    const c = b.weights.crypto;
    assert.ok(c <= E.CRYPTO_CAP[p.crypto] + 1e-9);
    assert.ok(c <= b.growth / 10 + 1e-9);
    if (p.crypto === 'none' || p.horizon < 4 || p.risk === 1) assert.equal(c, 0);
  });
  assert.equal(E.baseAllocation({ horizon: 20, risk: 5, crypto: 'high' }).weights.crypto, 9);     // a tenth of 90
  assert.equal(E.baseAllocation({ horizon: 20, risk: 4, crypto: 'high' }).weights.crypto, 8);
  assert.equal(E.baseAllocation({ horizon: 20, risk: 4, crypto: 'medium' }).weights.crypto, 5);
  assert.equal(E.baseAllocation({ horizon: 20, risk: 2, crypto: 'high' }).weights.crypto, 2);     // cautious: half of a tenth of 40
  assert.equal(E.baseAllocation({ horizon: 5, risk: 4, crypto: 'medium' }).weights.crypto, 2.5);  // 4 to 6 years: half
  assert.equal(E.baseAllocation({ horizon: 3, risk: 5, crypto: 'high' }).weights.crypto, 0);
});

test('gold waits for a three-year horizon and cash stays small over decades', () => {
  assert.equal(E.baseAllocation({ horizon: 2, risk: 3 }).weights.gold, 0);
  assert.equal(E.baseAllocation({ horizon: 3, risk: 3 }).weights.gold, 3);    // growth capped at 35
  assert.equal(E.baseAllocation({ horizon: 20, risk: 3 }).weights.gold, 5);
  everyProfile((p) => { if (p.horizon >= 10) assert.ok(E.baseAllocation(p).weights.cash <= 5 + 1e-9); });
  const cautious = E.baseAllocation({ horizon: 30, risk: 1, crypto: 'none' });
  assert.equal(cautious.weights.cash, 5);
  assert.equal(cautious.weights.bonds, 72);
});

// --------------------------------------------------------------------- leans

test('leaned mix sums to 100, stays non-negative and inside every cap for extreme readings', () => {
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
      E.RISKY.forEach((s) => assert.ok(w[s] <= base.weights[s] * (1 + E.STYLE[style].up) + 1e-9, `${s} leaned past its bound`));
    }
  });
});

test('steady style ignores every signal', () => {
  const prof = { horizon: 10, risk: 3, crypto: 'medium', style: 'steady' };
  const base = E.baseAllocation(prof);
  const w = E.tilt(base, scoresOf(-1), prof);
  E.SLEEVES.forEach((k) => near(w[k], base.weights[k], 1e-9));
});

test('trimming goes further than adding, and what is trimmed waits in cash', () => {
  const prof = { horizon: 8, risk: 2, crypto: 'none', style: 'balanced' };   // room on both sides of every cap
  const base = E.baseAllocation(prof);
  const down = E.tilt(base, scoresOf({ gold: -1 }), prof);
  near(down.gold, base.weights.gold * 0.65);
  near(down.cash - base.weights.cash, base.weights.gold * 0.35);
  near(down.us, base.weights.us);
  const up = E.tilt(base, scoresOf({ us: 1 }), prof);
  near(up.us, base.weights.us * 1.20);
  near(base.weights.cash - up.cash, base.weights.us * 0.20);
  assert.ok(E.STYLE.balanced.down > E.STYLE.balanced.up);
  assert.ok(E.STYLE.active.down <= 0.5, 'even the strongest setting never cuts a part by more than half');
});

test('active leans further than balanced, by the stated amounts', () => {
  const mk = (style, v) => {
    const prof = { horizon: 8, risk: 2, crypto: 'none', style };
    const base = E.baseAllocation(prof);
    return E.tilt(base, scoresOf({ bonds: v }), prof).bonds / base.weights.bonds;
  };
  near(mk('balanced', -1), 0.65);
  near(mk('active', -1), 0.50);
  near(mk('active', -0.5), 0.75);
});

test('rounding keeps the total at exactly 100', () => {
  everyProfile((p) => {
    for (const style of STYLES) {
      const prof = { ...p, style };
      const r = E.roundWeights(E.tilt(E.baseAllocation(prof), scoresOf({ us: 0.46, intl: 0.0, crypto: -0.42, gold: -0.87, bonds: -0.46 }), prof));
      assert.equal(sum(r), 100);
      E.SLEEVES.forEach((k) => assert.ok(Number.isInteger(r[k]) && r[k] >= 0));
    }
  });
  assert.equal(E.roundWeights(ZERO).cash, 100);
});

// ---------------------------------------------------------------------- news

test('news can only make the plan more careful', () => {
  const snap = (v) => ({ sleeves: { us: { score: v } } });
  const brief = (e) => ({ generatedAt: '2026-11-12T12:00:00Z', sleeveScores: { us: { score: e } } });
  const us = (s, e) => E.blendScores(snap(s), brief(e), NOW).us;
  near(us(0.5, -1).final, 0.9 * 0.5 - 0.1);        // gloomier news trims a positive lean by a tenth
  assert.equal(us(0.5, 1).final, 0.5);             // rosier news is ignored
  assert.equal(us(0.5, 1).eventUsed, false);
  assert.equal(us(0.05, -1).final, 0);             // it can cancel a positive lean but never flip it
  near(us(-0.5, -1).final, -0.55);                 // it can deepen a negative lean, by a tenth at most
  assert.equal(us(-0.5, 0.5).final, -0.5);
  near(us(0.5, -1).eventEffect, -0.15);
  // no price reading: bad news counts for a tenth, good news for nothing
  const none = (e) => E.blendScores({ sleeves: {} }, brief(e), NOW).us.final;
  near(none(-1), -0.1);
  assert.equal(none(1), 0);
  // the most news can ever do is a tenth of a full reading
  for (const s of [-1, -0.5, 0, 0.5, 1]) for (const e of [-1, 0, 1]) assert.ok(Math.abs(us(s, e).final - s) <= 0.2 + 1e-9 && us(s, e).final <= s + 1e-9);
});

test('a stale or missing brief changes nothing', () => {
  const snap = { sleeves: { us: { score: 0.5 }, bonds: { score: -1 } } };
  const stale = E.blendScores(snap, { generatedAt: '2026-11-01T12:00:00Z', sleeveScores: { us: { score: -1 } } }, NOW);
  assert.equal(stale.us.final, 0.5);
  assert.equal(E.blendScores(snap, null, NOW).bonds.final, -1);
  assert.equal(E.briefIsFresh(null, NOW), false);
  assert.equal(E.briefIsFresh({ generatedAt: 'nonsense' }, NOW), false);
  assert.equal(E.blendScores({ sleeves: { us: { score: 7 } } }, null, NOW).us.final, 1);   // clamped
});

// ------------------------------------------------------------- buying, bands

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
  const b = E.buyPlan(target, { ...ZERO, us: 900, bonds: 100 }, 1000);
  near(b.buys.bonds, 900);
  near(b.buys.us, 100);
  near(sum(b.buys), 1000);
  assert.equal(b.trims.length, 0);
  // too lopsided for new money to fix: everything goes to bonds and stocks are still flagged
  const heavy = E.buyPlan(target, { ...ZERO, us: 5000 }, 1000);
  near(heavy.buys.bonds, 1000);
  assert.equal(heavy.trims[0].key, 'us');
  near(heavy.trims[0].over, 5000 / 6000 * 100 - 50);
});

test('the drift band is 5 points, or a quarter of the target, and never under 1', () => {
  assert.equal(E.driftBand(40), 5);
  assert.equal(E.driftBand(10), 2.5);
  assert.equal(E.driftBand(2), 1);          // a 2% crypto slice is flagged at 3%, one and a half times target
  assert.equal(E.driftBand(0), 1);
  const target = { us: 60, intl: 0, crypto: 2, gold: 0, bonds: 38, cash: 0 };
  const inside = E.buyPlan(target, { ...ZERO, us: 6400, crypto: 280, bonds: 3320 }, 0);
  assert.equal(inside.trims.length, 0);     // stocks 4 points over, crypto 0.8 over: leave both alone
  const outside = E.buyPlan(target, { ...ZERO, us: 6000, crypto: 400, bonds: 3600 }, 0);
  assert.deepEqual(outside.trims.map((t) => t.key), ['crypto']);
});

test('pacing: lump sum by default, steps only for a nervous answer, never because of the market', () => {
  const target = { us: 40, intl: 20, crypto: 2, gold: 5, bonds: 23, cash: 10 };
  const P = (o) => E.normalizeProfile(o);
  assert.equal(E.pacing(P({ amount: 10000, risk: 3 }), target).mode, 'now');
  assert.equal(E.pacing(P({ amount: 10000, risk: 5 }), target).mode, 'now');
  assert.equal(E.pacing(P({ amount: 10000, risk: 2 }), target).steps, 3);
  assert.equal(E.pacing(P({ amount: 10000, risk: 1 }), target).steps, 6);
  assert.equal(E.pacing(P({ amount: 300, risk: 1 }), target).why, 'small');
  assert.equal(E.pacing(P({ amount: 10000, risk: 3 }), { ...target, cash: 100 }).why, 'cash');
  assert.equal(E.pacing.length, 3, 'profile, target and a currency threshold: no market data at all');
});

// ---------------------------------------------------------------------- risk

test('stress test: three scenarios, the gain needed to recover, and bonds that do not always help', () => {
  const half = E.stressTest({ ...ZERO, us: 50, cash: 50 });
  assert.deepEqual(half.scenarios.map((s) => s.id), ['crisis', 'inflation', 'worst']);
  near(half.pct, -25.5);
  const sixty = E.stressTest({ ...ZERO, us: 60, bonds: 40 });
  const by = Object.fromEntries(sixty.scenarios.map((s) => [s.id, s]));
  near(by.crisis.pct, 0.6 * -51 + 0.4 * 6);        // 2008: bonds rose and cushioned the fall
  near(by.inflation.pct, 0.6 * -19 + 0.4 * -13);   // 2022: they fell together
  assert.ok(by.inflation.parts.bonds < 0 && by.crisis.parts.bonds > 0);
  // a 50% loss needs a 100% gain to get back to even
  near(E.stressTest({ ...ZERO, us: 100 }).scenarios.find((s) => s.id === 'worst').recover, 51 / 49 * 100, 1e-9);
  assert.equal(E.stressTest({ ...ZERO, cash: 100 }).scenarios[2].recover, 0);
  assert.ok(E.WORST.crypto <= -85);
});

test('risk shares add to one and match a hand-worked two-asset case', () => {
  const half = E.riskShares({ ...ZERO, us: 50, cash: 50 }, null);
  near(sum(half.shares), 1, 1e-9);
  assert.ok(half.shares.us > 0.99);
  near(half.vol, Math.sqrt(0.25 * 0.16 * 0.16 + 0.25 * 0.01 * 0.01), 1e-9);
  const live = { vol: { us: 0.2, intl: 0.2, crypto: 0.65, gold: 0.2, bonds: 0.2, cash: 0.01 }, corr: { us: { intl: 0 }, intl: { us: 0 } } };
  const even = E.riskShares({ ...ZERO, us: 50, intl: 50 }, live);
  near(even.shares.us, 0.5, 1e-9);
  near(even.vol, Math.sqrt(2 * 0.25 * 0.04), 1e-9);
  assert.equal(even.live, true);
});

test('a small crypto slice carries a far larger share of the risk', () => {
  const r = E.riskShares({ us: 40, intl: 20, crypto: 5, gold: 5, bonds: 25, cash: 5 }, null);
  assert.ok(r.shares.crypto > 0.12, `crypto share ${r.shares.crypto}`);
  assert.ok(r.shares.bonds < 0.05);
  near(sum(r.shares), 1, 1e-9);
  // at a tenth of the mix, crypto is around a third of the risk
  const ten = E.riskShares({ us: 50, intl: 25, crypto: 10, gold: 5, bonds: 10, cash: 0 }, null);
  assert.ok(ten.shares.crypto > 0.25 && ten.shares.crypto < 0.45, `crypto share ${ten.shares.crypto}`);
});

test('a calm recent spell never makes a part look safer than its history', () => {
  const calm = { vol: { us: 0.05, intl: 0.05, crypto: 0.10, gold: 0.05, bonds: 0.01, cash: 0.001 }, corr: {} };
  near(E.riskShares({ ...ZERO, us: 100 }, calm).vol, E.LONG_RUN_VOL.us, 1e-9);
  near(E.riskShares({ ...ZERO, us: 100 }, { vol: { us: 0.40 }, corr: {} }).vol, 0.40, 1e-9);
  const none = E.riskShares(ZERO, null);
  assert.equal(none.vol, 0);
  assert.equal(none.shares.us, 0);
});

test('a part that moves against the rest carries a negative share', () => {
  const hedge = { vol: { us: 0.2, bonds: 0.1 }, corr: { us: { bonds: -0.9 }, bonds: { us: -0.9 } } };
  const r = E.riskShares({ ...ZERO, us: 80, bonds: 20 }, hedge);
  assert.ok(r.shares.bonds < 0);
  near(r.shares.us + r.shares.bonds, 1, 1e-9);
});

// ----------------------------------------------------------------- the future

test('future value matches the textbook formulas', () => {
  near(E.futureValue(1000, 0, 10, 0.07).value, 1000 * Math.pow(1.07, 10), 1e-6);
  near(E.futureValue(0, 100, 10, 0).value, 12000, 1e-9);
  assert.equal(E.futureValue(0, 100, 10, 0).paidIn, 12000);
  const i = Math.pow(1.06, 1 / 12) - 1;
  near(E.futureValue(0, 100, 1, 0.06).value, 100 * (Math.pow(1 + i, 12) - 1) / i, 1e-9);
  near(E.futureValue(1000, 100, 5, 0.05).value, E.futureValue(1000, 0, 5, 0.05).value + E.futureValue(0, 100, 5, 0.05).value, 1e-6);
  assert.equal(E.futureValue('x', -5, 'y', 0.05).value, 0);
  // the worked example from the research: $200 a month for 40 years at 5% after inflation is about $297,000
  assert.ok(Math.abs(E.futureValue(0, 200, 40, 0.05).value - 297000) < 2500);
  // starting ten years earlier roughly doubles the result at 7%
  assert.ok(E.futureValue(0, 100, 40, 0.07).value > 1.9 * E.futureValue(0, 100, 30, 0.07).value);
});

test('fee drag: one percent a year for forty years takes about a third', () => {
  near(E.feeDrag(40, 0.07, 0.01), 1 - Math.pow(1.06 / 1.07, 40), 1e-12);
  assert.ok(E.feeDrag(40, 0.07, 0.01) > 0.30 && E.feeDrag(40, 0.07, 0.01) < 0.33);
  assert.equal(E.feeDrag(40, 0.07, 0), 0);
  assert.ok(E.feeDrag(40, 0.07, 0.0003) < 0.012);
});

test('expected returns are built from today\'s starting points', () => {
  const snap = { macro: { cape: 40, y5y: 4.95, y3m: 4.1 } };
  const e = E.expectedReal(snap, 10);
  near(e.us, 2.5);                       // 100 / 40
  near(e.bonds, 4.95 - 2.5);             // starting yield less assumed inflation
  assert.equal(e.crypto, 0);             // no earnings or interest to forecast from
  assert.equal(e.gold, 1);
  assert.equal(e.live, true);
  near(E.expectedReal(snap, 1).cash, 4.1 - 2.5);            // near term: what bills pay now
  near(E.expectedReal(snap, 30).cash, 0.1 * 1.6 + 0.9 * 0.5); // decades: mostly the long-run 0.5%
  near(E.expectedReal({ macro: { cape: 15, y5y: 4.95 } }, 10).us, 100 / 15);
  assert.equal(E.expectedReal({ macro: { cape: 200 } }, 10).us, 1.5);   // floors and ceilings hold at the extremes
  assert.equal(E.expectedReal({ macro: { cape: 5 } }, 10).us, 7);
  const blank = E.expectedReal(null, 10);
  assert.equal(blank.live, false);
  assert.equal(blank.us, 3.5);
});

test('outlook: a range in today\'s money that includes what is already held', () => {
  const snap = { macro: { cape: 40, y5y: 4.95, y3m: 4.1 } };
  const target = { us: 40, intl: 20, crypto: 2, gold: 4, bonds: 24, cash: 10 };
  const o = E.outlook(target, snap, { amount: 1000, monthly: 200, horizon: 20, holdings: { ...ZERO, us: 4000 } }, 0.11);
  assert.ok(o.low < o.mid && o.mid < o.high);
  assert.ok(o.value.low < o.value.mid && o.value.mid < o.value.high);
  assert.equal(o.start, 5000);
  assert.equal(o.paidIn, 5000 + 200 * 240);
  near(o.value.mid, E.futureValue(5000, 200, 20, o.mid / 100).value, 1e-6);
  near(o.spread, 11 / Math.sqrt(20), 1e-9);
  const exp = E.expectedReal(snap, 20);
  near(o.mid, E.SLEEVES.reduce((a, k) => a + target[k] * exp[k] / 100, 0), 1e-9);
  // the yearly range narrows as the horizon lengthens
  assert.ok(E.outlook(target, snap, { horizon: 30 }, 0.11).spread < E.outlook(target, snap, { horizon: 5 }, 0.11).spread);
  assert.ok(o.feeDrag > 0.15 && o.feeDrag < 0.2);
});

test('three-fund version keeps the same split between stocks and the rest', () => {
  const s = E.threeFund({ us: 40, intl: 20, crypto: 2, gold: 4, bonds: 24, cash: 10 });
  assert.equal(s.us + s.intl + s.bonds, 100);
  assert.equal(s.stocks, 62);
  assert.equal(s.us, 40);
  assert.equal(E.threeFund({ ...ZERO, cash: 100 }).bonds, 100);
});

// ------------------------------------------------------------------ the whole

test('profile input is sanitised', () => {
  const p = E.normalizeProfile({ amount: 'abc', monthly: -50, horizon: -5, risk: 99, crypto: 'yolo', style: 'x', unstable: 1, holdings: { us: -3, bonds: '250' } });
  assert.equal(p.amount, 1000);
  assert.equal(p.monthly, 0);
  assert.equal(p.horizon, 0);
  assert.equal(p.risk, 5);
  assert.equal(p.crypto, 'small');
  assert.equal(p.style, 'balanced');
  assert.equal(p.unstable, true);
  assert.equal(p.holdings.us, 0);
  assert.equal(p.holdings.bonds, 250);
});

test('full plan is coherent and flags what needs attention first', () => {
  const snap = {
    regime: { score: -0.12 }, macro: { vix: 18, cape: 40.2, y5y: 4.95, y3m: 4.13 },
    sleeves: { us: { score: 0.46 }, intl: { score: 0.0 }, crypto: { score: -0.42 }, gold: { score: -0.87 }, bonds: { score: -0.46 } }
  };
  const brief = { generatedAt: '2026-11-12T17:00:00Z', sleeveScores: { us: { score: -0.15 }, bonds: { score: -0.6 }, crypto: { score: -0.7 }, gold: { score: -0.5 }, intl: { score: -0.25 } } };
  const pl = E.plan({ amount: 5000, monthly: 200, horizon: 12, risk: 3, crypto: 'medium', style: 'balanced', efund: false, debt: true }, snap, brief, NOW);
  assert.equal(sum(pl.target), 100);
  near(sum(pl.buy.buys), 5000, 1e-6);
  assert.deepEqual(pl.checks.map((c) => c.id), ['debt', 'efund']);
  const row = Object.fromEntries(pl.rows.map((r) => [r.key, r]));
  assert.equal(row.gold.stance, 'under');
  assert.equal(row.bonds.stance, 'under');
  assert.equal(row.cash.stance, 'extra');
  assert.ok(row.us.target >= row.us.base);
  assert.ok(row.us.eventEffect < 0, 'gloomier news trimmed the stock lean');
  near(sum(Object.fromEntries(pl.rows.map((r) => [r.key, r.riskShare]))), 1, 1e-9);
  assert.equal(pl.stress.scenarios.length, 3);
  assert.ok(pl.outlook.value.mid > pl.outlook.paidIn * 0.9);
  assert.equal(pl.simple.us + pl.simple.intl + pl.simple.bonds, 100);
  assert.deepEqual(pl.lean, { down: 0.35, up: 0.20 });
  // a large crypto slice is flagged by the share of risk it carries, not by its size alone
  const big = E.plan({ horizon: 20, risk: 5, crypto: 'high' }, null, null, NOW);
  assert.ok(big.checks.some((c) => c.id === 'crypto'));
  assert.ok(!E.plan({ horizon: 20, risk: 3, crypto: 'small' }, null, null, NOW).checks.some((c) => c.id === 'crypto'));
  // an empty snapshot degrades to the baseline rather than throwing
  const bare = E.plan({ horizon: 12, risk: 3 }, null, null, NOW);
  assert.deepEqual(bare.target, bare.baseRounded);
});

// ------------------------------------------------------------ your situation

test('costly debt is cleared first, then the cushion, then the rest is invested', () => {
  const sit = (o) => ({ amount: 10000, situation: { spending: 4000, savings: 5000, debt: 3000, debtRate: 12, ...o } });
  const f = E.firstThings(sit({}));
  assert.equal(f.toDebt, 3000);                 // the whole overdraft goes first
  assert.equal(f.toSavings, 7000);              // cushion is 3 x 4,000 = 12,000; 5,000 is there already
  assert.equal(f.invest, 0);
  assert.equal(f.gapLeft, 0);
  assert.equal(f.known, true);
  // cheap debt is left alone: a 4% loan costs less than the plan expects to earn
  const cheap = E.firstThings(sit({ debtRate: 4 }));
  assert.equal(cheap.toDebt, 0);
  assert.equal(cheap.costly, false);
  assert.equal(cheap.toSavings, 7000);
  assert.equal(cheap.invest, 3000);
  // exactly at the line counts as costly
  assert.equal(E.firstThings(sit({ debtRate: E.DEBT_FIRST_RATE })).toDebt, 3000);
  // a debt larger than the deposit takes all of it and reports what is left
  const big = E.firstThings(sit({ debt: 25000 }));
  assert.equal(big.toDebt, 10000);
  assert.equal(big.debtLeft, 15000);
  assert.equal(big.invest, 0);
});

test('the cushion is six months when income is irregular or self-employed', () => {
  const base = { amount: 100000, situation: { spending: 5000, savings: 0 } };
  assert.equal(E.firstThings(base).cushion, 15000);
  assert.equal(E.firstThings({ ...base, unstable: true }).cushion, 30000);
  assert.equal(E.firstThings({ ...base, situation: { ...base.situation, status: 'self' } }).cushion, 30000);
  assert.equal(E.firstThings({ ...base, situation: { spending: 5000, savings: 20000 } }).toSavings, 0);
  assert.equal(E.firstThings({ ...base, situation: { spending: 5000, savings: 10000 } }).monthsSaved, 2);
});

test('with no figures entered, nothing is redirected and the yes/no warnings still apply', () => {
  const f = E.firstThings({ amount: 2000 });
  assert.equal(f.known, false);
  assert.equal(f.invest, 2000);
  assert.equal(f.monthsSaved, null);
  const warned = E.plan({ amount: 2000, debt: true, efund: false }, null, null, NOW);
  assert.deepEqual(warned.checks.map((c) => c.id), ['debt', 'efund']);
  // once real figures exist they replace the warnings
  const real = E.plan({ amount: 2000, debt: true, efund: false, situation: { spending: 3000, savings: 20000 } }, null, null, NOW);
  assert.ok(!real.checks.some((c) => c.id === 'debt' || c.id === 'efund'));
});

test('the plan invests only what is left after debt and cushion', () => {
  const pl = E.plan({ amount: 10000, horizon: 10, risk: 3, situation: { spending: 2000, savings: 3000, debt: 1500, debtRate: 11 } }, null, null, NOW);
  assert.equal(pl.first.toDebt, 1500);
  assert.equal(pl.first.toSavings, 3000);
  assert.equal(pl.first.invest, 5500);
  near(sum(pl.buy.buys), 5500, 1e-6);
  assert.equal(pl.outlook.start, 5500);
  // nothing left to invest: every buy is zero and pacing has nothing to time
  const none = E.plan({ amount: 1000, situation: { debt: 5000, debtRate: 15 } }, null, null, NOW);
  assert.equal(sum(none.buy.buys), 0);
  assert.equal(none.pacing.why, 'cash');
});

test('situation input is sanitised', () => {
  const p = E.normalizeProfile({ country: 'mars', situation: { status: 'astronaut', income: 'lots', spending: -5, debtRate: 500, studyFund: 'maybe', pension: 'yes' } });
  assert.equal(p.country, 'IL');
  assert.equal(E.normalizeProfile({ country: 'other' }).country, 'other');
  assert.equal(p.situation.status, 'employee');
  assert.equal(p.situation.income, 0);
  assert.equal(p.situation.spending, 0);
  assert.equal(p.situation.debtRate, 100);
  assert.equal(p.situation.studyFund, 'unsure');
  assert.equal(p.situation.pension, 'yes');
  assert.deepEqual(Object.keys(E.normalizeProfile({}).situation).sort(), ['debt', 'debtRate', 'income', 'pension', 'savings', 'spending', 'status', 'studyFund']);
});

test('local yields replace dollar ones for the steady part, and nothing else', () => {
  const snap = { macro: { cape: 40, y5y: 4.95, y3m: 4.1 } };
  const us = E.expectedReal(snap, 10);
  const il = E.expectedReal(snap, 10, { cash: 3.25, bond: 4.0, inflation: 2 });
  assert.equal(il.us, us.us);
  assert.equal(il.gold, us.gold);
  near(il.bonds, 2.0);
  near(il.cash, 0.3 * 1.25 + 0.7 * 0.5);
  assert.equal(il.inflation, 2);
  assert.equal(us.inflation, E.INFLATION_ASSUMED);
  const o = E.outlook({ us: 0, intl: 0, crypto: 0, gold: 0, bonds: 100, cash: 0 }, snap, { horizon: 10 }, 0.06, { bond: 4.0, inflation: 2 });
  near(o.mid, 2.0);
  assert.equal(o.inflation, 2);
});

test('a part with no usable signal stays at its baseline', () => {
  const snap = { sleeves: { us: { score: 0.5 }, bonds: { score: -1 }, gold: { score: -1 } } };
  const brief = { generatedAt: '2026-11-12T17:00:00Z', sleeveScores: { bonds: { score: -1 } } };
  const prof = { horizon: 8, risk: 2, crypto: 'none' };
  const withSignal = E.plan(prof, snap, brief, NOW);
  const without = E.plan(prof, snap, brief, NOW, { noSignal: ['bonds'] });
  const row = (pl, k) => pl.rows.find((r) => r.key === k);
  assert.ok(row(withSignal, 'bonds').target < row(withSignal, 'bonds').base);
  assert.equal(row(without, 'bonds').target, row(without, 'bonds').base);
  assert.equal(row(without, 'bonds').unread, true);
  assert.equal(row(without, 'gold').target, row(withSignal, 'gold').target);   // other parts are untouched
});

test('a part read from another market ignores the US news brief', () => {
  const snap = { sleeves: { us: { score: 0.4 }, bonds: { score: 0.6 }, gold: { score: 0.3 } } };
  const brief = { generatedAt: '2026-11-12T17:00:00Z', sleeveScores: { bonds: { score: -1 }, gold: { score: -1 } } };
  const prof = { horizon: 8, risk: 2, crypto: 'none' };
  const braked = E.plan(prof, snap, brief, NOW);
  const local = E.plan(prof, snap, brief, NOW, { noEvent: ['bonds'] });
  const row = (pl, k) => pl.rows.find((r) => r.key === k);
  assert.ok(row(braked, 'bonds').score < 0.6);                 // the brief brakes it by default
  near(row(local, 'bonds').score, 0.6);                        // the local reading stands as it is
  assert.equal(row(local, 'bonds').event, null);
  assert.equal(row(local, 'bonds').eventEffect, 0);
  assert.equal(row(local, 'bonds').local, true);
  assert.equal(row(local, 'bonds').unread, false);
  near(row(local, 'gold').score, row(braked, 'gold').score);   // other parts still hear the news
  // with no reading at all there is nothing to keep, and noSignal still wins
  const none = E.plan(prof, { sleeves: { us: { score: 0.4 } } }, brief, NOW, { noEvent: ['bonds'] });
  assert.equal(row(none, 'bonds').score, 0);
  const off = E.plan(prof, snap, brief, NOW, { noSignal: ['bonds'], noEvent: ['bonds'] });
  assert.equal(row(off, 'bonds').unread, true);
});

test('money for a home gets a lower ceiling on shares for each year remaining', () => {
  assert.deepEqual([1, 2.5, 4, 6, 8].map((y) => E.horizonCap(y, 'home')), [0, 15, 30, 45, 60]);
  assert.deepEqual([10, 15, 30].map((y) => E.horizonCap(y, 'home')), [85, 90, 90]);        // far enough away: the usual rule
  [1, 2.5, 4, 6, 8].forEach((y) => assert.ok(E.horizonCap(y, 'home') <= E.horizonCap(y), 'home cap above the usual one at ' + y));
  const growth = (o) => { const w = E.baseAllocation(o).weights; return w.us + w.intl + w.crypto; };
  const saver = { horizon: 4, risk: 5, crypto: 'high' };
  near(growth(saver), 35);
  near(growth(Object.assign({ goal: 'home' }, saver)), 30);
  // the cap also binds after the readings lean the mix
  const snap = { sleeves: { us: { score: 1 }, intl: { score: 1 } } };
  const pl = E.plan(Object.assign({ goal: 'home', style: 'active' }, saver), snap, null, NOW);
  assert.ok(pl.target.us + pl.target.intl + pl.target.crypto <= 30);
  // no crypto for a purchase inside five years
  assert.equal(E.baseAllocation({ goal: 'home', horizon: 4.5, risk: 5, crypto: 'high' }).weights.crypto, 0);
  assert.ok(E.baseAllocation({ horizon: 4.5, risk: 5, crypto: 'high' }).weights.crypto > 0);
  assert.equal(E.normalizeProfile({ goal: 'yacht' }).goal, 'growth');
});

test('purchase tax is charged on the slice in each band', () => {
  const b = [[1978745, 0], [2347040, 3.5], [6055070, 5], [20183565, 8], [Infinity, 10]];
  assert.equal(E.purchaseTax(1500000, b), 0);
  near(E.purchaseTax(2000000, b), (2000000 - 1978745) * 0.035);
  near(E.purchaseTax(2500000, b), (2347040 - 1978745) * 0.035 + (2500000 - 2347040) * 0.05);
  assert.equal(E.purchaseTax(2500000, null), 0);
});

test('the home goal adds up the cash needed and measures the gap', () => {
  const rules = { ltv: 0.75, costs: 0.03, brackets: [[1978745, 0], [2347040, 3.5], [Infinity, 5]] };
  assert.equal(E.homeGoal({ goal: 'home' }, rules, 0), null);                      // no price, no goal
  const g = E.homeGoal({ goal: 'home', homePrice: 2000000, horizon: 5, monthly: 3000 }, rules, 100000);
  near(g.down, 500000);
  near(g.costs, 60000);
  near(g.tax, (2000000 - 1978745) * 0.035);
  near(g.need, g.down + g.costs + g.tax);
  near(g.gap, g.need - 100000);
  near(g.loan, 1500000);
  near(g.monthlyNeeded, g.gap / 60);
  near(g.yearsAtPace, g.gap / 36000);
  assert.equal(g.onTrack, false);                                                 // 3,000 a month for 5 years is 180,000
  const done = E.homeGoal({ homePrice: 1000000, horizon: 3, monthly: 0 }, rules, 400000);
  assert.equal(done.gap, 0);
  assert.equal(done.onTrack, true);
  assert.equal(done.yearsAtPace, 0);
  assert.equal(E.homeGoal({ homePrice: 1000000, horizon: 3, monthly: 0 }, rules, 0).yearsAtPace, null);
});

test('forecasts are scored against a coin and against the naive rule', () => {
  const f = (pUp, up, base, inRange) => ({ pUp, up, base, inRange, horizonDays: 7 });
  const none = E.scoreForecasts([]);
  assert.equal(none.n, 0);
  assert.equal(none.brier, null);
  assert.equal(none.verdict, 'early');
  const s = E.scoreForecasts([f(0.7, true, 0.55, true), f(0.4, false, 0.55, false), f(0.6, false, 0.55, true), f(0.5, true, 0.55, null)]);
  assert.equal(s.n, 4);
  assert.equal(s.calls, 3);                       // a flat 50% is not a call either way
  assert.equal(s.hits, 2);
  near(s.brier, (0.09 + 0.16 + 0.36 + 0.25) / 4);
  near(s.baseBrier, (0.2025 + 0.3025 + 0.3025 + 0.2025) / 4);
  near(s.skill, 1 - s.brier / s.baseBrier);
  near(s.inRange, 2 / 3);
  assert.equal(s.verdict, 'early');               // four forecasts prove nothing
  // perfect calls beat the naive rule once there are enough of them; confident wrong ones lose to it
  const good = Array.from({ length: 60 }, (_, i) => f(i % 2 ? 0.9 : 0.1, i % 2 === 1, 0.5, true));
  assert.equal(E.scoreForecasts(good).verdict, 'ahead');
  const bad = Array.from({ length: 60 }, (_, i) => f(i % 2 ? 0.1 : 0.9, i % 2 === 1, 0.5, true));
  assert.equal(E.scoreForecasts(bad).verdict, 'behind');
  const same = Array.from({ length: 60 }, (_, i) => f(0.55, i % 2 === 1, 0.55, true));
  assert.equal(E.scoreForecasts(same).verdict, 'level');
  // broken rows are ignored rather than counted
  assert.equal(E.scoreForecasts([{ pUp: 'high', up: true }, { pUp: 0.6 }, null, f(0.6, true, null, null)]).n, 1);
  assert.equal(E.scoreForecasts([f(0.6, true, null, null)]).skill, null);
  // calls corrected by the record are scored beside the raw ones, on the same calls
  const adj = E.scoreForecasts([Object.assign(f(0.8, false, 0.5, true), { pAdj: 0.6 }), f(0.7, true, 0.5, true)]);
  assert.equal(adj.adjN, 1);
  near(adj.adjBrier, 0.36);
  near(adj.adjRawBrier, 0.64);
  assert.equal(E.scoreForecasts([f(0.7, true, 0.5, true)]).adjBrier, null);
  assert.equal(Object.keys(E.scoreForecasts([f(0.6, true, 0.5, true), Object.assign(f(0.6, true, 0.5, true), { horizonDays: 30 })]).byHorizon).length, 2);
});

test('the "too small to split" line follows the currency', () => {
  const target = { us: 60, intl: 0, crypto: 0, gold: 0, bonds: 40, cash: 0 };
  const P = (o) => E.normalizeProfile(o);
  assert.equal(E.pacing(P({ amount: 1000, risk: 1 }), target).steps, 6);            // 1,000 dollars: worth stepping in
  assert.equal(E.pacing(P({ amount: 1000, risk: 1 }), target, 1800).why, 'small');  // 1,000 shekels: not worth it
  assert.equal(E.pacing(P({ amount: 5000, risk: 1 }), target, 1800).steps, 6);
});
