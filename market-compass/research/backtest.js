#!/usr/bin/env node
/* Run the page's own engine over the replayed history from history_fetch.py.

     node backtest.js history.json [--json out.json]

   Each month-end the engine is given that day's readings and asked for a plan,
   exactly as the page asks it. The plan is held for the following month, then
   reset. Compared: the same person with signals off ("steady"), on at the default
   setting ("balanced") and on at the stronger one ("active").

   Costs: every reset is charged 0.10% of what it trades. Real people following the
   page trade less than this, because the page tells them to rebalance with new
   money and to act only when a part has drifted by 5 points.

   Read the result with care. One stretch of history, in one country's funds, proves
   little, and the rules were written knowing how that history went. */
'use strict';
const fs = require('fs');
const path = require('path');
const E = require(path.join(__dirname, '..', 'app', 'src', 'engine.js'));

const COST = 0.001;
const KEYS = E.SLEEVES;

function simulate(rows, profile, opts) {
  opts = opts || {};
  let value = 1, peak = 1, maxDD = 0, turnover = 0, held = null;
  const curve = [], monthly = [], growthShare = [], cashShare = [];
  rows.forEach((row) => {
    const sleeves = {};
    Object.keys(row.scores).forEach((k) => { if (row.scores[k] !== null) sleeves[k] = { score: row.scores[k] }; });
    if (opts.only) Object.keys(sleeves).forEach((k) => { if (opts.only.indexOf(k) < 0) delete sleeves[k]; });
    const pl = E.plan(profile, { sleeves: sleeves }, null, Date.parse(row.asOf + 'T21:00:00Z'));
    const w = {};
    KEYS.forEach((k) => { w[k] = pl.target[k] / 100; });
    // a part with no price history yet waits in cash
    KEYS.forEach((k) => { if (k !== 'cash' && row.ret[k] === null && w[k] > 0) { w.cash += w[k]; w[k] = 0; } });
    if (opts.fixed) KEYS.forEach((k) => { w[k] = opts.fixed[k] || 0; });
    if (held) {
      const traded = KEYS.reduce((a, k) => a + Math.abs(w[k] - held[k]), 0) / 2;
      turnover += traded;
      value *= 1 - traded * COST;
    }
    let r = 0;
    KEYS.forEach((k) => { r += w[k] * (row.ret[k] === null ? 0 : row.ret[k]); });
    value *= 1 + r;
    monthly.push(r);
    // what the holdings drift to before the next reset
    held = {};
    KEYS.forEach((k) => { held[k] = w[k] * (1 + (row.ret[k] === null ? 0 : row.ret[k])) / (1 + r); });
    peak = Math.max(peak, value);
    maxDD = Math.min(maxDD, value / peak - 1);
    curve.push({ m: row.next, v: value });
    growthShare.push(w.us + w.intl + w.crypto);
    cashShare.push(w.cash);
  });
  const n = monthly.length, years = n / 12;
  const mean = monthly.reduce((a, b) => a + b, 0) / n;
  const sd = Math.sqrt(monthly.reduce((a, b) => a + (b - mean) * (b - mean), 0) / (n - 1));
  let worst12 = 0;
  for (let i = 12; i < curve.length; i++) worst12 = Math.min(worst12, curve[i].v / curve[i - 12].v - 1);
  const avg = (a) => a.reduce((x, y) => x + y, 0) / a.length;
  return {
    cagr: Math.pow(value, 1 / years) - 1, vol: sd * Math.sqrt(12), maxDD: maxDD, worst12: worst12, final: value,
    turnover: turnover / years, growth: avg(growthShare), cash: avg(cashShare), curve: curve, monthly: monthly
  };
}

/** Fall from the highest month-end inside a window to the lowest one after it. */
function fallIn(curve, from, to) {
  const seg = curve.filter((p) => p.m >= from && p.m <= to);
  let peak = -Infinity, dd = 0;
  seg.forEach((p) => { peak = Math.max(peak, p.v); dd = Math.min(dd, p.v / peak - 1); });
  return dd;
}
function gainIn(curve, from, to) {
  const a = curve.filter((p) => p.m < from).pop(), b = curve.filter((p) => p.m <= to).pop();
  return a && b ? b.v / a.v - 1 : null;
}

const EPISODES = [
  { id: 'dotcom', name: 'Dot-com bust', from: '2000-03', to: '2002-10' },
  { id: 'gfc', name: 'Financial crisis', from: '2007-10', to: '2009-03' },
  { id: 'covid', name: 'Covid crash', from: '2020-01', to: '2020-04' },
  { id: 'inflation', name: '2022 inflation', from: '2021-12', to: '2022-10' }
];
const RALLIES = [
  { id: 'r2003', name: 'Recovery of 2003', from: '2003-03', to: '2004-03' },
  { id: 'r2009', name: 'Recovery of 2009', from: '2009-03', to: '2010-03' },
  { id: 'r2020', name: 'Recovery of 2020', from: '2020-04', to: '2021-04' }
];

const PERIODS = [
  { name: '1997 to 2006', from: '1997-06', to: '2006-12' },
  { name: '2007 to 2012', from: '2007-01', to: '2012-12' },
  { name: '2013 to 2019', from: '2013-01', to: '2019-12' },
  { name: '2020 to 2026', from: '2020-01', to: '2099-12' }
];

function run(file) {
  const data = JSON.parse(fs.readFileSync(file, 'utf8'));
  const rows = data.rows;
  const out = { from: rows[0].next, to: rows[rows.length - 1].next, months: rows.length, cost: COST, cases: [] };
  const people = [
    { id: 'cautious', label: 'Cautious (risk answer 2)', profile: { horizon: 20, risk: 2, crypto: 'none' } },
    { id: 'middle', label: 'Middle (risk answer 3)', profile: { horizon: 20, risk: 3, crypto: 'none' } },
    { id: 'bold', label: 'Bold (risk answer 5)', profile: { horizon: 20, risk: 5, crypto: 'none' } }
  ];
  people.forEach((person) => {
    const c = { id: person.id, label: person.label, styles: {} };
    ['steady', 'balanced', 'active'].forEach((style) => {
      const p = Object.assign({}, person.profile, { style: style });
      const s = simulate(rows, p);
      c.styles[style] = summary(s);
      c.styles[style].episodes = EPISODES.map((e) => ({ id: e.id, name: e.name, fall: +fallIn(s.curve, e.from, e.to).toFixed(4) }));
      c.styles[style].rallies = RALLIES.map((e) => ({ id: e.id, name: e.name, gain: +gainIn(s.curve, e.from, e.to).toFixed(4) }));
      if (person.id === 'middle') c.styles[style].curve = s.curve.filter((_, i, a) => i % 3 === 0 || i === a.length - 1).map((p) => ({ m: p.m, v: +p.v.toFixed(4) }));
      // how often the leaning mix came out ahead over rolling five-year spans
      c.styles[style].monthly = s.monthly;
    });
    const base = c.styles.steady.monthly;
    ['balanced', 'active'].forEach((style) => {
      const m = c.styles[style].monthly;
      let ahead = 0, spans = 0;
      for (let i = 60; i <= m.length; i++) {
        let a = 1, b = 1;
        for (let j = i - 60; j < i; j++) { a *= 1 + m[j]; b *= 1 + base[j]; }
        spans++; if (a > b) ahead++;
      }
      c.styles[style].aheadOver5y = ahead / spans;
    });
    Object.keys(c.styles).forEach((k) => { delete c.styles[k].monthly; });
    out.cases.push(c);
  });
  // the middle person, period by period: the rules were published partway through this history
  const mid = { horizon: 20, risk: 3, crypto: 'none' };
  out.periods = PERIODS.map((pd) => {
    const seg = rows.filter((r) => r.next >= pd.from && r.next <= pd.to);
    const o = { name: pd.name, from: seg[0].next, to: seg[seg.length - 1].next, styles: {} };
    ['steady', 'balanced', 'active'].forEach((style) => { o.styles[style] = summary(simulate(seg, Object.assign({}, mid, { style: style }))); });
    return o;
  });
  // which part's reading did the work: lean on one part at a time
  out.attribution = {};
  ['us', 'intl', 'bonds', 'gold'].forEach((k) => {
    out.attribution[k] = summary(simulate(rows, Object.assign({}, mid, { style: 'balanced' }), { only: [k] }));
  });
  // calendar years in which leaning came out ahead of not leaning
  const byYear = {};
  const sA = simulate(rows, Object.assign({}, mid, { style: 'steady' })), sB = simulate(rows, Object.assign({}, mid, { style: 'balanced' }));
  rows.forEach((r, i) => {
    const y = r.next.slice(0, 4);
    byYear[y] = byYear[y] || { steady: 1, balanced: 1 };
    byYear[y].steady *= 1 + sA.monthly[i]; byYear[y].balanced *= 1 + sB.monthly[i];
  });
  out.years = Object.keys(byYear).sort().map((y) => ({ y: y, steady: +(byYear[y].steady - 1).toFixed(4), balanced: +(byYear[y].balanced - 1).toFixed(4) }));
  // yardsticks
  out.yardsticks = {
    usStocks: summary(simulate(rows, {}, { fixed: { us: 1 } })),
    sixtyForty: summary(simulate(rows, {}, { fixed: { us: 0.6, bonds: 0.4 } })),
    cash: summary(simulate(rows, {}, { fixed: { cash: 1 } }))
  };
  // crypto, over the years it has existed: the same middle person with and without a 5% ceiling
  const since = rows.filter((r) => r.next >= '2016-01');
  out.crypto = { from: since[0].next, to: since[since.length - 1].next, styles: {} };
  [['none', 'steady'], ['medium', 'steady'], ['medium', 'balanced']].forEach((pair) => {
    out.crypto.styles[pair[0] + '-' + pair[1]] = summary(simulate(since, { horizon: 20, risk: 3, crypto: pair[0], style: pair[1] }));
  });
  return out;
}
function summary(s) {
  const r = (x, d) => +x.toFixed(d || 4);
  return { cagr: r(s.cagr), vol: r(s.vol), maxDD: r(s.maxDD), worst12: r(s.worst12), final: r(s.final, 3), turnover: r(s.turnover, 3), growth: r(s.growth, 3), cash: r(s.cash, 3) };
}

if (require.main === module) {
  const file = process.argv[2] || path.join(__dirname, 'history.json');
  const out = run(file);
  // --late FILE: a second replay whose readings were taken well before each month-end (see --lag
  // in history_fetch.py), to show how much being slow would have cost.
  const l = process.argv.indexOf('--late');
  if (l > 0) {
    const lateData = JSON.parse(fs.readFileSync(process.argv[l + 1], 'utf8'));
    out.late = { days: lateData.lag, balanced: summary(simulate(lateData.rows, { horizon: 20, risk: 3, crypto: 'none', style: 'balanced' })) };
    console.log('Readings ' + out.late.days + ' trading days old, middle balanced: ' + (out.late.balanced.cagr * 100).toFixed(1) + '% a year, worst fall ' + (out.late.balanced.maxDD * 100).toFixed(1) + '%\n');
  }
  const j = process.argv.indexOf('--json');
  if (j > 0) fs.writeFileSync(process.argv[j + 1], JSON.stringify(out));
  const pc = (x) => (x * 100).toFixed(1).padStart(6) + '%';
  console.log('Months ' + out.months + ', ' + out.from + ' to ' + out.to + ', trading cost ' + (COST * 100) + '%\n');
  console.log('                              yearly   swings  worst    worst    ends   trades  stocks   cash   ahead of');
  console.log('                              return           fall     year     at     /year   avg      avg    steady, 5y');
  out.cases.forEach((c) => {
    Object.keys(c.styles).forEach((k) => {
      const s = c.styles[k];
      console.log((c.label + ' ' + k).padEnd(30) + pc(s.cagr) + ' ' + pc(s.vol) + ' ' + pc(s.maxDD) + ' ' + pc(s.worst12) + ' ' + String(s.final).padStart(7) + ' ' + pc(s.turnover) + ' ' + pc(s.growth) + ' ' + pc(s.cash) + (s.aheadOver5y === undefined ? '' : '   ' + pc(s.aheadOver5y)));
    });
    console.log('   falls:   ' + EPISODES.map((e, i) => e.name + ' ' + ['steady', 'balanced', 'active'].map((k) => pc(c.styles[k].episodes[i].fall).trim()).join(' / ')).join('  |  '));
    console.log('   rallies: ' + RALLIES.map((e, i) => e.name + ' ' + ['steady', 'balanced', 'active'].map((k) => pc(c.styles[k].rallies[i].gain).trim()).join(' / ')).join('  |  ') + '\n');
  });
  console.log('Middle person by period (steady / balanced / active):');
  out.periods.forEach((pd) => {
    const f = (key) => ['steady', 'balanced', 'active'].map((k) => pc(pd.styles[k][key]).trim()).join(' / ');
    console.log('  ' + pd.name.padEnd(14) + ' return ' + f('cagr').padEnd(24) + ' worst fall ' + f('maxDD'));
  });
  console.log('\nLeaning on one part only (middle, balanced): ' + Object.keys(out.attribution).map((k) => k + ' ' + pc(out.attribution[k].cagr).trim() + ' / fall ' + pc(out.attribution[k].maxDD).trim()).join('  |  '));
  const won = out.years.filter((y) => y.balanced > y.steady).length;
  console.log('Calendar years leaning was ahead: ' + won + ' of ' + out.years.length);
  console.log('  ' + out.years.map((y) => y.y.slice(2) + ':' + ((y.balanced - y.steady) * 100).toFixed(1)).join(' ') + '\n');
  Object.keys(out.yardsticks).forEach((k) => { const s = out.yardsticks[k]; console.log(('yardstick ' + k).padEnd(30) + pc(s.cagr) + ' ' + pc(s.vol) + ' ' + pc(s.maxDD) + ' ' + pc(s.worst12) + ' ' + String(s.final).padStart(7)); });
  console.log('\nCrypto years, ' + out.crypto.from + ' to ' + out.crypto.to);
  Object.keys(out.crypto.styles).forEach((k) => { const s = out.crypto.styles[k]; console.log(('  ' + k).padEnd(30) + pc(s.cagr) + ' ' + pc(s.vol) + ' ' + pc(s.maxDD) + ' ' + pc(s.worst12) + ' ' + String(s.final).padStart(7)); });
}
module.exports = { run: run, simulate: simulate };
