'use strict';
/* Checks that the history test adds up. Run: node --test backtest.test.js */
const test = require('node:test');
const assert = require('node:assert/strict');
const { simulate } = require('./backtest.js');

const near = (a, b, eps) => assert.ok(Math.abs(a - b) < (eps || 1e-9), a + ' is not near ' + b);
const row = (i, ret, scores) => ({
  asOf: '2020-' + String((i % 12) + 1).padStart(2, '0') + '-28', next: String(2020 + Math.floor((i + 1) / 12)) + '-' + String(((i + 1) % 12) + 1).padStart(2, '0'),
  scores: scores || { us: null, intl: null, bonds: null, gold: null, crypto: null },
  ret: Object.assign({ us: 0, intl: 0, bonds: 0, gold: 0, crypto: 0, cash: 0 }, ret)
});

test('fixed weights compound the weighted return', () => {
  const rows = Array.from({ length: 24 }, (_, i) => row(i, { us: 0.02, bonds: 0.005 }));
  const s = simulate(rows, {}, { fixed: { us: 0.5, bonds: 0.5 } });
  // every month earns 1.25% before the small cost of resetting the weights
  assert.ok(s.final < Math.pow(1.0125, 24) && s.final > Math.pow(1.0125, 24) * 0.999);
  near(s.maxDD, 0);
  assert.ok(s.turnover > 0 && s.turnover < 0.05);
});

test('the worst fall is measured from the highest point before it', () => {
  const path = [0.10, -0.20, -0.10, 0.30, 0.05];
  const s = simulate(path.map((r, i) => row(i, { us: r })), {}, { fixed: { us: 1 } });
  near(s.maxDD, 0.8 * 0.9 - 1);
  near(s.final, 1.1 * 0.8 * 0.9 * 1.3 * 1.05);
  near(s.turnover, 0);                      // one holding never needs resetting
});

test('a part with no price history waits in cash', () => {
  const rows = Array.from({ length: 12 }, (_, i) => row(i, { gold: null, us: 0.01, intl: 0.01, bonds: 0.01, cash: 0.01 }));
  const s = simulate(rows, { horizon: 20, risk: 3, crypto: 'none', style: 'steady' });
  near(s.final, Math.pow(1.01, 12), 1e-3);  // everything earned 1%, so gold's share did too, as cash
  assert.ok(s.cash > 0.09);                 // the 5% for gold sits with the 5% already in cash
});

test('readings move the mix only when signals are switched on', () => {
  const scores = { us: -1, intl: -1, bonds: 0, gold: 0, crypto: null };
  const rows = Array.from({ length: 12 }, (_, i) => row(i, { us: -0.05, intl: -0.05 }, scores));
  const off = simulate(rows, { horizon: 20, risk: 3, crypto: 'none', style: 'steady' });
  const on = simulate(rows, { horizon: 20, risk: 3, crypto: 'none', style: 'balanced' });
  near(off.growth, 0.60);
  near(on.growth, 0.39, 0.011);             // a full negative reading trims stocks by 35% of their size
  assert.ok(on.final > off.final);
});
