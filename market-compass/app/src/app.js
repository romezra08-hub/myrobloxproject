/* Market Compass page logic. Reads the snapshot and brief from the artifact's
 * data store, runs the engine for the viewer's profile, and draws everything.
 * Text that comes from the data store is always inserted as text, never markup. */
(function () {
  'use strict';
  var E = window.MCEngine;
  var CFG = window.MC_CONFIG || {};
  var VIEWS = ['plan', 'markets', 'crypto', 'events', 'ask', 'method'];
  var MINUS = '−';
  var STALE_H = 30;            // older than this, prices are flagged as out of date
  var IGNORE_SIGNALS_D = 14;   // older than this, signals no longer move the plan
  var COLOR = { us: 'var(--c-us)', intl: 'var(--c-intl)', crypto: 'var(--c-crypto)', gold: 'var(--c-gold)', bonds: 'var(--c-bonds)', cash: 'var(--c-cash)' };
  var HOLD_WITH = {
    us: 'A total-market or S&P 500 index fund, such as VTI, VOO or FSKAX.',
    intl: 'A total international index fund, such as VXUS or IXUS.',
    crypto: 'Mostly Bitcoin, with a smaller share of Ether if you want it. A spot fund such as IBIT or FBTC, or a large regulated exchange.',
    gold: 'A low-cost gold fund, such as IAU or GLDM.',
    bonds: 'A broad bond index fund, such as BND or AGG. BSV is a shorter, steadier version.',
    cash: 'A high-yield savings account, a money-market fund, or a T-bill fund such as SGOV or BIL.'
  };

  var S = {
    snap: null, brief: null, profile: E.normalizeProfile(E.DEFAULTS), view: 'plan',
    data: 'loading',            // loading | live | slow | off
    open: {},                   // which allocation rows are expanded
    caps: { db: null, user: null, sample: null, mcp: null }, uid: null,
    turns: [], asking: null, refreshState: null
  };

  // ------------------------------------------------------------------ helpers
  function h(tag, attrs) {
    var el = document.createElement(tag);
    setAttrs(el, attrs);
    for (var i = 2; i < arguments.length; i++) append(el, arguments[i]);
    return el;
  }
  function sv(tag, attrs) {
    var el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    setAttrs(el, attrs);
    for (var i = 2; i < arguments.length; i++) append(el, arguments[i]);
    return el;
  }
  function setAttrs(el, attrs) {
    if (!attrs) return;
    Object.keys(attrs).forEach(function (k) {
      var v = attrs[k];
      if (v === null || v === undefined || v === false) return;
      if (k === 'class') el.setAttribute('class', v);
      else if (k === 'style' && typeof v === 'object') Object.keys(v).forEach(function (p) { el.style.setProperty(p, v[p]); });
      else if (k.slice(0, 2) === 'on' && typeof v === 'function') el.addEventListener(k.slice(2), v);
      else if (v === true) el.setAttribute(k, '');
      else el.setAttribute(k, String(v));
    });
  }
  function append(el, kid) {
    if (kid === null || kid === undefined || kid === false) return;
    if (Array.isArray(kid)) { kid.forEach(function (k) { append(el, k); }); return; }
    el.appendChild(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  function $(id) { return document.getElementById(id); }
  function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }
  function isNum(x) { return typeof x === 'number' && isFinite(x); }
  function str(x, max) { return typeof x === 'string' ? x.slice(0, max || 2000).replace(/(^|[\s(])-(?=\d)/g, '$1' + MINUS) : ''; }
  function safeUrl(u) { return typeof u === 'string' && /^https?:\/\//i.test(u) ? u : null; }
  function link(text, url) {
    var u = safeUrl(url);
    return u ? h('a', { href: u, target: '_blank', rel: 'noopener noreferrer' }, text) : document.createTextNode(text);
  }

  function nf(x, d) { return x.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }); }
  function pct(x, d, signed) {
    if (!isNum(x)) return '–';
    d = d === undefined ? 1 : d;
    var v = x * 100, a = Math.abs(v).toFixed(d);
    if (Number(a) === 0) return a + '%';
    return (v < 0 ? MINUS : (signed === false ? '' : '+')) + a + '%';
  }
  function signedNum(x, d) {
    if (!isNum(x)) return '–';
    var a = Math.abs(x).toFixed(d === undefined ? 2 : d);
    if (Number(a) === 0) return a;
    return (x < 0 ? MINUS : '+') + a;
  }
  function money(x) {
    if (!isNum(x)) return '–';
    var a = Math.abs(x);
    return (x < 0 ? MINUS : '') + '$' + nf(a, a > 0 && a < 100 && Math.round(a) !== a ? 2 : 0);
  }
  function moneyBig(x) {
    if (!isNum(x)) return '–';
    var a = Math.abs(x);
    if (a >= 1e12) return '$' + nf(x / 1e12, 2) + 'T';
    if (a >= 1e9) return '$' + nf(x / 1e9, a >= 1e11 ? 0 : 1) + 'B';
    if (a >= 1e6) return '$' + nf(x / 1e6, 1) + 'M';
    return money(x);
  }
  function price(x) {
    if (!isNum(x)) return '–';
    var a = Math.abs(x);
    return nf(x, a >= 10000 ? 0 : a >= 1 ? 2 : a >= 0.01 ? 4 : 6);
  }
  function dirClass(x) { return !isNum(x) || Math.abs(x) < 5e-5 ? '' : x > 0 ? 'up' : 'down'; }
  function parseTime(iso) { var t = Date.parse(iso); return isFinite(t) ? t : null; }
  function dateShort(iso) {
    var t = parseTime(/^\d{4}-\d{2}-\d{2}$/.test(iso || '') ? iso + 'T12:00:00Z' : iso);
    return t === null ? '' : new Date(t).toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: /^\d{4}-\d{2}-\d{2}$/.test(iso) ? 'UTC' : undefined });
  }
  function dateTime(iso) {
    var t = parseTime(iso);
    return t === null ? '' : new Date(t).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' });
  }
  function ago(iso) {
    var t = parseTime(iso);
    if (t === null) return '';
    var m = Math.max(0, Math.round((Date.now() - t) / 60000));
    if (m < 1) return 'just now';
    if (m < 60) return m + ' min ago';
    var hr = Math.round(m / 60);
    if (hr < 36) return hr + ' h ago';
    return Math.round(hr / 24) + ' days ago';
  }
  function ageHours(iso) { var t = parseTime(iso); return t === null ? Infinity : (Date.now() - t) / 3.6e6; }
  function years(n) { return n < 1 ? 'under a year' : n === 1 ? '1 year' : n + ' years'; }
  function list(words) {
    if (words.length <= 1) return words.join('');
    return words.slice(0, -1).join(', ') + ' and ' + words[words.length - 1];
  }

  function icon(kind) {
    var p = {
      up: 'M5 1.5 L9 8 H1 Z', down: 'M5 8.5 L1 2 H9 Z', flat: 'M1.5 4 H8.5 V6 H1.5 Z',
      stop: 'M5 0.6 L9.6 9 H0.4 Z', info: 'M5 0.5 A4.5 4.5 0 1 0 5 9.5 A4.5 4.5 0 1 0 5 0.5 Z'
    }[kind];
    return sv('svg', { width: kind === 'stop' || kind === 'info' ? 16 : 9, height: kind === 'stop' || kind === 'info' ? 16 : 9, viewBox: '0 0 10 10', 'aria-hidden': 'true', class: 'ico' },
      sv('path', { d: p, fill: 'currentColor' }));
  }
  function chip(text, tone, ico) {
    return h('span', { class: 'chip' + (tone ? ' ' + tone : '') }, ico ? h('span', { class: 'ico-' + (tone || 'mid') }, icon(ico)) : null, text);
  }
  function scoreTone(s) { return !isNum(s) ? '' : s >= 0.15 ? 'pos' : s <= -0.15 ? 'neg' : ''; }
  function scoreWord(s) {
    if (!isNum(s)) return 'No reading';
    return s >= 0.5 ? 'Favorable' : s >= 0.15 ? 'Leaning positive' : s > -0.15 ? 'Neutral' : s > -0.5 ? 'Leaning negative' : 'Unfavorable';
  }
  function scoreChip(s) { var t = scoreTone(s); return chip(scoreWord(s), t, t === 'pos' ? 'up' : t === 'neg' ? 'down' : 'flat'); }
  function dv(score) {
    var el = h('div', { class: 'dv', role: 'img', 'aria-label': isNum(score) ? 'Reading ' + signedNum(score, 2) + ' on a scale from minus one to plus one' : 'No reading' });
    if (isNum(score) && Math.abs(score) >= 0.02) {
      el.appendChild(h('i', { class: score > 0 ? 'p' : 'n', style: { width: (Math.min(1, Math.abs(score)) * 50).toFixed(1) + '%' } }));
    }
    el.title = isNum(score) ? signedNum(score, 2) : 'No reading';
    return el;
  }
  function tile(label, value, note, noteClass) {
    return h('div', { class: 'tile' }, h('div', { class: 'tile-label' }, label), h('div', { class: 'tile-value' }, value),
      note ? h('div', { class: 'tile-note' + (noteClass ? ' ' + noteClass : '') }, note) : null);
  }
  function card(title, sub) {
    var c = h('section', { class: 'card stack' });
    if (title) c.appendChild(h('h2', null, title));
    if (sub) c.appendChild(h('p', { class: 'sub' }, sub));
    for (var i = 2; i < arguments.length; i++) append(c, arguments[i]);
    return c;
  }
  function emptyState(text) { return h('section', { class: 'card' }, h('p', { class: 'empty' }, text)); }

  // ------------------------------------------------------------------- charts
  function sparkline(values, color) {
    var w = 88, hh = 24, pad = 3;
    if (!Array.isArray(values) || values.length < 2) return h('span', null, '');
    var mn = Math.min.apply(null, values), mx = Math.max.apply(null, values), span = mx - mn || 1;
    var pts = values.map(function (v, i) {
      return (pad + i * (w - 2 * pad - 3) / (values.length - 1)).toFixed(1) + ',' + (pad + (1 - (v - mn) / span) * (hh - 2 * pad)).toFixed(1);
    });
    var last = pts[pts.length - 1].split(',');
    return sv('svg', { class: 'spark', width: w, height: hh, viewBox: '0 0 ' + w + ' ' + hh, 'aria-hidden': 'true' },
      sv('polyline', { points: pts.join(' '), fill: 'none', 'stroke-width': 1.5, 'stroke-linejoin': 'round', 'stroke-linecap': 'round', style: { stroke: color || 'var(--muted)' } }),
      sv('circle', { cx: last[0], cy: last[1], r: 2.4, style: { fill: color || 'var(--muted)' } }));
  }

  function niceStep(span, target) {
    var raw = span / target, mag = Math.pow(10, Math.floor(Math.log10(raw))), n = raw / mag;
    return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * mag;
  }

  /* Chart observers are tracked per view so a re-render can release the old ones. */
  var ROS = { markets: [], crypto: [] }, roBucket = null;
  function dropObservers(name) { ROS[name].forEach(function (r) { r.disconnect(); }); ROS[name] = []; }

  /* Line chart with a crosshair readout, drawn at its real pixel width so text never scales.
     series: [{name, color, values, width}], labels: [text per point]. */
  function lineChart(o) {
    var H = o.height || 150, L = 38, R = 10, T = 8, B = 20;
    var all = [];
    o.series.forEach(function (s) { all = all.concat(s.values.filter(isNum)); });
    if (all.length < 2) return h('p', { class: 'empty' }, 'Not enough history to draw.');
    var mn = Math.min.apply(null, all), mx = Math.max.apply(null, all);
    var step = niceStep((mx - mn) || 1, 3);
    var lo = Math.floor(mn / step) * step, hi = Math.ceil(mx / step) * step;
    if (hi === lo) hi = lo + step;
    var n = o.series[0].values.length;
    var tip = h('div', { class: 'tip', hidden: true });
    var wrap = h('div', { class: 'chart', style: { 'min-height': H + 'px' } });
    var drawn = 0;

    function draw(width) {
      var W = Math.max(220, Math.round(width));
      if (Math.abs(W - drawn) < 2) return;
      drawn = W;
      var X = function (i) { return L + i * (W - L - R) / (n - 1); };
      var Y = function (v) { return T + (1 - (v - lo) / (hi - lo)) * (H - T - B); };
      var svg = sv('svg', { width: W, height: H, viewBox: '0 0 ' + W + ' ' + H, role: 'img', tabindex: '0', 'aria-label': o.label || 'Line chart' });
      for (var v = lo; v <= hi + step / 1e6; v += step) {
        var isBase = o.baseline !== undefined && Math.abs(v - o.baseline) < step / 1e6;
        svg.appendChild(sv('line', { x1: L, x2: W - R, y1: Y(v), y2: Y(v), class: isBase ? 'axis-line' : 'grid-line' }));
        svg.appendChild(sv('text', { x: L - 6, y: Y(v) + 3.5, 'text-anchor': 'end' }, o.tick ? o.tick(v) : String(v)));
      }
      if (o.xLabels) {
        svg.appendChild(sv('text', { x: L, y: H - 5, 'text-anchor': 'start' }, o.xLabels[0]));
        svg.appendChild(sv('text', { x: W - R, y: H - 5, 'text-anchor': 'end' }, o.xLabels[1]));
      }
      o.series.forEach(function (s, si) {
        var d = '';
        s.values.forEach(function (val, i) { if (isNum(val)) d += (d ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(val).toFixed(1); });
        if (si === 0 && o.area) {
          svg.appendChild(sv('path', { d: d + 'L' + X(n - 1).toFixed(1) + ' ' + Y(lo) + 'L' + X(0).toFixed(1) + ' ' + Y(lo) + 'Z', style: { fill: s.color, opacity: 0.1 }, stroke: 'none' }));
        }
        svg.appendChild(sv('path', { d: d, fill: 'none', 'stroke-width': s.width || 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round', style: { stroke: s.color } }));
      });
      var first = o.series[0];
      svg.appendChild(sv('circle', { cx: X(n - 1), cy: Y(first.values[n - 1]), r: 4, 'stroke-width': 2, style: { fill: first.color, stroke: 'var(--surface)' } }));

      var cross = sv('line', { y1: T, y2: H - B, class: 'axis-line', visibility: 'hidden' });
      var dots = o.series.map(function (s) { return sv('circle', { r: 3.5, 'stroke-width': 2, visibility: 'hidden', style: { fill: s.color, stroke: 'var(--surface)' } }); });
      svg.appendChild(cross);
      dots.forEach(function (d) { svg.appendChild(d); });
      var hit = sv('rect', { x: L, y: T, width: W - L - R, height: H - T - B, fill: 'transparent' });
      svg.appendChild(hit);
      var at = n - 1;
      function show(i) {
        at = Math.max(0, Math.min(n - 1, i));
        cross.setAttribute('x1', X(at)); cross.setAttribute('x2', X(at)); cross.setAttribute('visibility', 'visible');
        clear(tip);
        tip.appendChild(h('div', null, o.labels ? o.labels[at] : ''));
        var top = lo;
        o.series.forEach(function (s, si) {
          var val = s.values[at];
          dots[si].setAttribute('visibility', isNum(val) ? 'visible' : 'hidden');
          if (!isNum(val)) return;
          top = Math.max(top, val);
          dots[si].setAttribute('cx', X(at)); dots[si].setAttribute('cy', Y(val));
          tip.appendChild(h('div', null, h('span', { class: 'k', style: { background: s.color } }), h('b', null, o.fmt ? o.fmt(val) : String(val)), ' ' + s.name));
        });
        var box = svg.getBoundingClientRect(), sx = box.width / W;
        tip.style.left = Math.max(74, Math.min(box.width - 74, X(at) * sx)) + 'px';
        tip.style.top = (Y(top) * sx) + 'px';
        tip.hidden = false;
      }
      function hide() { tip.hidden = true; cross.setAttribute('visibility', 'hidden'); dots.forEach(function (d) { d.setAttribute('visibility', 'hidden'); }); }
      hit.addEventListener('pointermove', function (ev) {
        var box = svg.getBoundingClientRect();
        show(Math.round(((ev.clientX - box.left) / box.width * W - L) / ((W - L - R) / (n - 1))));
      });
      hit.addEventListener('pointerleave', hide);
      svg.addEventListener('focus', function () { show(n - 1); });
      svg.addEventListener('blur', hide);
      svg.addEventListener('keydown', function (ev) {
        if (ev.key === 'ArrowLeft') { show(at - 1); ev.preventDefault(); }
        if (ev.key === 'ArrowRight') { show(at + 1); ev.preventDefault(); }
      });
      clear(wrap);
      tip.hidden = true;
      wrap.appendChild(svg);
      wrap.appendChild(tip);
    }

    if (typeof ResizeObserver === 'function') {
      var ro = new ResizeObserver(function (entries) { var w = entries[0].contentRect.width; if (w > 0) draw(w); });
      ro.observe(wrap);
      if (roBucket) roBucket.push(ro);
    } else {
      draw(340);
    }
    return wrap;
  }

  function trendChart(key, ch, height) {
    var idx = function (v) { return v - 100; };
    return lineChart({
      height: height, baseline: 0, area: true,
      label: E.LABELS[key] + ', one year, against its 200-day average',
      series: [
        { name: 'Price', color: COLOR[key], values: ch.px.map(idx) },
        { name: '200-day average', color: 'var(--muted)', values: ch.ma.map(idx), width: 1.5 }
      ],
      labels: (ch.dates || []).map(dateShort),
      xLabels: [dateShort(ch.from), dateShort(ch.to)],
      tick: function (v) { var r = Math.round(v * 10) / 10; return (r > 0 ? '+' : r < 0 ? MINUS : '') + Math.abs(r) + '%'; },
      fmt: function (v) { return pct(v / 100, 1); }
    });
  }

  function polar(cx, cy, r, deg) { var a = deg * Math.PI / 180; return [cx + r * Math.cos(a), cy - r * Math.sin(a)]; }
  function arc(cx, cy, r, a0, a1) {
    var p0 = polar(cx, cy, r, a0), p1 = polar(cx, cy, r, a1);
    return 'M' + p0[0].toFixed(1) + ' ' + p0[1].toFixed(1) + ' A' + r + ' ' + r + ' 0 0 1 ' + p1[0].toFixed(1) + ' ' + p1[1].toFixed(1);
  }
  /* The compass: a half-dial from risk-off to risk-on with the needle on the current reading. */
  function dial(score) {
    var cx = 120, cy = 118, r = 96;
    var ang = function (s) { return 180 - (s + 1) / 2 * 180; };
    var bands = [[-1, -0.5, 'var(--neg)'], [-0.5, -0.15, 'var(--neg-wash)'], [-0.15, 0.15, 'var(--mid-wash)'], [0.15, 0.5, 'var(--pos-wash)'], [0.5, 1, 'var(--pos)']];
    var svg = sv('svg', { viewBox: '0 0 240 146', role: 'img', class: 'dial', 'aria-label': 'Risk conditions dial reading ' + scoreWord(score) });
    bands.forEach(function (b) {
      svg.appendChild(sv('path', { d: arc(cx, cy, r, ang(b[0]) - 1, ang(b[1]) + 1), fill: 'none', 'stroke-width': 12, 'stroke-linecap': 'butt', style: { stroke: b[2] } }));
    });
    [-1, -0.5, 0, 0.5, 1].forEach(function (t) {
      var a = polar(cx, cy, r - 12, ang(t)), b = polar(cx, cy, r - 18, ang(t));
      svg.appendChild(sv('line', { x1: a[0], y1: a[1], x2: b[0], y2: b[1], class: 'axis-line' }));
    });
    if (isNum(score)) {
      var tipP = polar(cx, cy, r - 24, ang(Math.max(-1, Math.min(1, score))));
      var l = polar(cx, cy, 7, ang(score) + 90), rr = polar(cx, cy, 7, ang(score) - 90);
      svg.appendChild(sv('path', { d: 'M' + l[0].toFixed(1) + ' ' + l[1].toFixed(1) + ' L' + tipP[0].toFixed(1) + ' ' + tipP[1].toFixed(1) + ' L' + rr[0].toFixed(1) + ' ' + rr[1].toFixed(1) + ' Z', style: { fill: 'var(--needle)' } }));
    }
    svg.appendChild(sv('circle', { cx: cx, cy: cy, r: 8, 'stroke-width': 2, style: { fill: 'var(--surface)', stroke: 'var(--ink)' } }));
    svg.appendChild(sv('text', { x: cx - r, y: 140, 'text-anchor': 'middle' }, 'Risk-off'));
    svg.appendChild(sv('text', { x: cx + r, y: 140, 'text-anchor': 'middle' }, 'Risk-on'));
    return h('div', { class: 'chart' }, svg);
  }

  function rankBars(items) {
    var max = Math.max.apply(null, items.map(function (i) { return Math.abs(i.value); })) || 1;
    return h('div', { class: 'bars' }, items.map(function (it) {
      return h('div', { class: 'bar-row', title: it.name + ': ' + pct(it.value) },
        h('span', null, it.name),
        h('span', { class: 'bar-track' }, h('i', { class: it.value >= 0 ? 'p' : 'n', style: { width: (Math.abs(it.value) / max * 50).toFixed(1) + '%' } })),
        h('span', { class: 'bar-val num ' + dirClass(it.value) }, pct(it.value)));
    }));
  }

  // --------------------------------------------------------------- data state
  function snapForEngine() {
    if (!S.snap) return null;
    return ageHours(S.snap.generatedAt) > IGNORE_SIGNALS_D * 24 ? null : S.snap;
  }
  function currentPlan() { return E.plan(S.profile, snapForEngine(), S.brief, Date.now()); }

  function renderFresh() {
    var el = clear($('fresh'));
    if (S.snap) {
      var old = ageHours(S.snap.generatedAt) > STALE_H;
      el.appendChild(h('span', { class: 'fresh-item', title: 'Prices fetched ' + dateTime(S.snap.generatedAt) },
        h('span', { class: 'dot ' + (old ? 'stale' : 'live') }), 'Prices ' + ago(S.snap.generatedAt)));
    } else {
      el.appendChild(h('span', { class: 'fresh-item' }, h('span', { class: 'dot' + (S.data === 'off' ? ' off' : '') }),
        S.data === 'off' ? 'Market data unavailable here' : S.data === 'slow' ? 'Still reaching market data' : S.data === 'empty' ? 'Waiting for the first data refresh' : 'Loading market data'));
    }
    if (S.brief && S.brief.generatedAt) {
      el.appendChild(h('span', { class: 'fresh-item', title: 'News brief written ' + dateTime(S.brief.generatedAt) },
        h('span', { class: 'dot ' + (E.briefIsFresh(S.brief, Date.now()) ? 'live' : 'stale') }), 'News brief ' + ago(S.brief.generatedAt)));
    }
    if (S.refreshReady) {
      var busy = S.refreshState === 'starting' || S.refreshState === 'started';
      el.appendChild(h('button', { class: 'btn small', id: 'refresh-btn', type: 'button', disabled: busy, onclick: fireRefresh },
        S.refreshState === 'starting' ? 'Starting…' : S.refreshState === 'started' ? 'Refresh running' : 'Refresh now'));
    }
    var b = $('banner');
    clear(b);
    var msg = null;
    if (S.refreshMsg) msg = S.refreshMsg;
    else if (S.data === 'off' && !S.snap) msg = ['Live data needs Claude. ', 'Open this page in Claude while signed in to load prices and news. Your baseline plan below still works without them.'];
    else if (S.data === 'slow' && !S.snap) msg = ['Still trying to reach the market data. ', 'Your baseline plan is shown meanwhile and will update when the data arrives.'];
    else if (S.snap && ageHours(S.snap.generatedAt) > IGNORE_SIGNALS_D * 24) msg = ['The market data is more than two weeks old. ', 'Signals are switched off until it is refreshed, so the plan shows your baseline mix.'];
    else if (S.snap && ageHours(S.snap.generatedAt) > 96) msg = ['Prices were last refreshed ' + ago(S.snap.generatedAt) + '. ', 'Trend readings move slowly, but check the date before acting.'];
    if (msg) { b.hidden = false; b.appendChild(h('div', { class: 'banner' }, h('span', null, h('strong', null, msg[0]), msg[1]))); }
    else b.hidden = true;
  }

  // --------------------------------------------------------------------- plan
  function buildControls() {
    var p = S.profile;
    function radioSet(name, options, current, cls) {
      var box = h('div', { class: cls });
      options.forEach(function (o) {
        var id = 'f-' + name + '-' + o[0];
        box.appendChild(h('input', { type: 'radio', name: name, id: id, value: o[0], checked: String(current) === String(o[0]) }));
        box.appendChild(h('label', { for: id }, o[1]));
      });
      return box;
    }
    var horizonOut = h('output', { for: 'f-horizon', class: 'num', id: 'f-horizon-out' }, years(p.horizon));
    var form = h('form', { class: 'card plan-controls stack', id: 'controls', autocomplete: 'off', onsubmit: function (e) { e.preventDefault(); } },
      h('h2', null, 'About you'),
      h('div', { class: 'field' }, h('label', { for: 'f-amount' }, 'Money to invest now'),
        h('div', { class: 'money' }, h('span', { 'aria-hidden': 'true' }, '$'), h('input', { id: 'f-amount', type: 'number', inputmode: 'decimal', min: '0', step: '50', value: p.amount }))),
      h('div', { class: 'field' },
        h('div', { class: 'row' }, h('label', { for: 'f-horizon', class: 'grow' }, 'When you will need it'), horizonOut),
        h('input', { id: 'f-horizon', type: 'range', min: '0', max: '40', step: '1', value: p.horizon }),
        h('span', { class: 'hint' }, 'The single biggest input. Money needed soon cannot ride out a crash.')),
      h('fieldset', { class: 'field' }, h('legend', null, 'If your investments fell 30% in a year, you would'),
        radioSet('risk', [[1, 'Sell everything'], [2, 'Sell some to feel safer'], [3, 'Hold, and lose sleep'], [4, 'Hold without much worry'], [5, 'Buy more']], p.risk, 'opt-list')),
      h('fieldset', { class: 'field' }, h('legend', null, 'Crypto, at most'),
        radioSet('crypto', [['none', 'None'], ['small', '2%'], ['medium', '5%'], ['high', '10%']], p.crypto, 'seg-ctl'),
        h('span', { class: 'hint' }, 'A ceiling, not a target. Large banks suggest 1 to 5% for those who want any.')),
      h('fieldset', { class: 'field' }, h('legend', null, 'How much should market signals move the plan'),
        radioSet('style', [['steady', 'Not at all'], ['balanced', 'A little'], ['active', 'A lot']], p.style, 'seg-ctl'),
        h('span', { class: 'hint', id: 'style-hint' }, '')),
      h('label', { class: 'check', for: 'f-efund' }, h('input', { type: 'checkbox', id: 'f-efund', checked: p.efund }), h('span', null, 'I have 3 to 6 months of spending set aside')),
      h('label', { class: 'check', for: 'f-debt' }, h('input', { type: 'checkbox', id: 'f-debt', checked: p.debt }), h('span', null, 'I have credit-card or other high-interest debt')),
      h('details', { class: 'plain', id: 'hold-details', open: E.SLEEVES.some(function (k) { return p.holdings[k] > 0; }) },
        h('summary', null, 'Already invested? Add what you hold'),
        h('div', { class: 'stack', style: { 'margin-top': '10px' } },
          h('p', { class: 'hint note' }, 'New money then goes to whatever is furthest below target, so you rebalance by buying.'),
          h('div', { class: 'hold-grid' }, E.SLEEVES.map(function (k) {
            return h('div', { class: 'field' }, h('label', { for: 'f-h-' + k }, E.LABELS[k]),
              h('div', { class: 'money' }, h('span', { 'aria-hidden': 'true' }, '$'), h('input', { id: 'f-h-' + k, type: 'number', inputmode: 'decimal', min: '0', step: '50', value: p.holdings[k] || '' })));
          })))),
      h('p', { class: 'note', id: 'save-note' }, ''));
    form.addEventListener('input', readControls);
    form.addEventListener('change', readControls);
    return form;
  }

  function readControls() {
    var f = $('controls');
    if (!f) return;
    var pick = function (name) { var el = f.querySelector('input[name="' + name + '"]:checked'); return el ? el.value : undefined; };
    var holdings = {};
    E.SLEEVES.forEach(function (k) { holdings[k] = Number($('f-h-' + k).value) || 0; });
    S.profile = E.normalizeProfile({
      amount: $('f-amount').value === '' ? 0 : Number($('f-amount').value), horizon: Number($('f-horizon').value),
      risk: Number(pick('risk')), crypto: pick('crypto'), style: pick('style'),
      efund: $('f-efund').checked, debt: $('f-debt').checked, holdings: holdings
    });
    $('f-horizon-out').textContent = years(S.profile.horizon);
    renderPlan();
    saveProfileSoon();
  }

  function writeControls() {
    var p = S.profile, f = $('controls');
    if (!f) return;
    if (document.activeElement !== $('f-amount')) $('f-amount').value = p.amount;
    $('f-horizon').value = p.horizon;
    $('f-horizon-out').textContent = years(p.horizon);
    [['risk', p.risk], ['crypto', p.crypto], ['style', p.style]].forEach(function (x) { var el = $('f-' + x[0] + '-' + x[1]); if (el) el.checked = true; });
    $('f-efund').checked = p.efund; $('f-debt').checked = p.debt;
    E.SLEEVES.forEach(function (k) { if (document.activeElement !== $('f-h-' + k)) $('f-h-' + k).value = p.holdings[k] || ''; });
    if (E.SLEEVES.some(function (k) { return p.holdings[k] > 0; })) $('hold-details').open = true;
  }

  function topDriver(parts, final) {
    var live = (parts || []).filter(function (p) { return isNum(p.score); });
    if (!live.length) return null;
    var same = live.filter(function (p) { return !isNum(final) || final === 0 || (p.score > 0) === (final > 0); });
    return (same.length ? same : live).slice().sort(function (a, b) { return Math.abs(b.score * b.weight) - Math.abs(a.score * a.weight); })[0];
  }

  function rowWhy(row, pl) {
    var snap = snapForEngine(), sl = snap && snap.sleeves && snap.sleeves[row.key];
    if (row.key === 'cash') {
      var y = sl && sl.parts && sl.parts[0] ? str(sl.parts[0].text, 200) : '';
      var lead = row.stance === 'extra' ? 'Holds what the signals trimmed elsewhere. ' : row.stance === 'less' ? 'Drawn on to fund stronger parts. ' : '';
      return lead + (y && y !== 'No reading' ? y + '.' : 'Your steady anchor and dry powder.');
    }
    if (row.stance === 'none') {
      if (row.key === 'crypto') return S.profile.crypto === 'none' ? 'You chose to hold none.' : 'Too volatile for money needed within ' + (S.profile.horizon < 3 ? '3' : '5') + ' years.';
      return 'Not part of a mix with this timeline.';
    }
    if (!sl) return 'No live reading, so this stays at its baseline.';
    var d = topDriver(sl.parts, row.score);
    return d ? str(d.text, 220) + '.' : 'No live reading, so this stays at its baseline.';
  }

  function rowDetail(row, pl) {
    var snap = snapForEngine(), sl = snap && snap.sleeves && snap.sleeves[row.key];
    var box = h('div', { class: 'alloc-detail' });
    var moved = row.target - row.base;
    box.appendChild(h('p', { class: 'sub' },
      'Baseline ' + row.base + '%. Now ' + row.target + '%' + (moved !== 0 ? ' (' + (moved > 0 ? '+' : MINUS) + Math.abs(moved) + (Math.abs(moved) === 1 ? ' point).' : ' points).') : '.') +
      (row.key !== 'cash' && isNum(row.score) && pl.k > 0 ? ' Overall reading ' + signedNum(row.score, 2) + ' on a scale of ' + MINUS + '1 to +1; at this setting a full reading moves a part by ' + Math.round(pl.k * 100) + '%.' : '') +
      (row.key !== 'cash' && pl.k === 0 ? ' Signals are shown for information and do not move your plan.' : '')));
    if (sl && sl.parts && row.key !== 'cash') {
      var parts = h('div', { class: 'parts' });
      sl.parts.forEach(function (p) {
        parts.appendChild(h('div', { class: 'part' }, h('span', { class: 'part-label' }, str(p.label, 60)), dv(p.score), h('span', { class: 'part-text' }, str(p.text, 260))));
        if (Array.isArray(p.detail)) {
          var bits = p.detail.filter(function (d) { return isNum(d.score); }).map(function (d) { return str(d.text, 120); });
          if (bits.length) parts.appendChild(h('p', { class: 'note' }, bits.join(' · ')));
        }
      });
      var ev = pl.eventsUsed && S.brief.sleeveScores && S.brief.sleeveScores[row.key];
      if (ev && isNum(ev.score)) {
        parts.appendChild(h('div', { class: 'part' }, h('span', { class: 'part-label' }, 'News and events'), dv(ev.score), h('span', { class: 'part-text' }, str(ev.why, 300))));
      }
      box.appendChild(parts);
      box.appendChild(h('p', { class: 'note' }, 'Price-based readings count for 80% and the news reading for 20%.'));
    }
    box.appendChild(h('p', { class: 'sub' }, h('b', null, 'How to hold it: '), HOLD_WITH[row.key], ' Examples, not endorsements.'));
    return box;
  }

  function summarySentence(pl) {
    if (!snapForEngine()) return 'Live signals are not available right now, so this is your baseline mix.';
    if (pl.k === 0) return 'This is your baseline mix. Market signals are shown for information and do not move it.';
    var up = [], down = [];
    pl.rows.forEach(function (r) {
      if (r.key === 'cash') return;
      if (r.stance === 'over') up.push(E.LABELS[r.key].toLowerCase().replace('us ', 'US '));
      if (r.stance === 'under') down.push(E.LABELS[r.key].toLowerCase().replace('us ', 'US '));
    });
    var cash = pl.rows.filter(function (r) { return r.key === 'cash'; })[0];
    if (!up.length && !down.length) return 'Signals are close to neutral, so the plan sits on your baseline mix.';
    var s = 'Compared with your baseline, today’s signals ';
    if (up.length) s += 'add to ' + list(up);
    if (up.length && down.length) s += ' and ';
    if (down.length) s += 'trim ' + list(down);
    s += '.';
    if (cash.tilt >= 2) s += ' ' + cash.tilt + ' extra points wait in T-bills.';
    return s;
  }

  var CHECK_COPY = {
    debt: ['Pay off high-interest debt before investing', function () { return 'A card charging 22% costs more than anything here can reliably earn, so clearing it is the best return available. Use this plan for money left after that.'; }],
    efund: ['Build a safety cushion first', function () {
      var y = S.snap && S.snap.macro && isNum(S.snap.macro.y3m) ? ' (T-bills currently pay about ' + S.snap.macro.y3m.toFixed(1) + '%)' : '';
      return 'Keep 3 to 6 months of spending in savings or T-bills' + y + ', so a surprise bill never forces you to sell investments at a bad moment. Then invest what is left.';
    }],
    short: ['Money needed within a year belongs in cash', function () { return 'Stocks can fall 20% or more in a single year. For money you need that soon, the plan keeps everything in savings or T-bills.'; }],
    horizon: ['Your timeline is setting the limit', function (pl) { return 'You could stomach more risk, but money needed in ' + years(pl.profile.horizon) + ' should not have more than ' + pl.base.growthCap + '% in stocks and crypto.'; }],
    crypto: ['A 10% crypto ceiling is a large bet', function () { return 'Bitcoin has fallen 75% or more three times. A repeat at this size would cost about 8 points of your whole portfolio.'; }]
  };
  function callout(level, title, text) {
    return h('div', { class: 'callout ' + level }, icon(level === 'info' ? 'info' : 'stop'), h('h3', null, title), h('p', null, text));
  }

  function renderPlan() {
    var hero = $('plan-hero'), rest = $('plan-rest');
    if (!hero) return;
    var pl = currentPlan(), p = pl.profile;
    clear(hero); clear(rest);

    pl.checks.filter(function (c) { return c.level === 'stop'; }).forEach(function (c) {
      hero.appendChild(callout('stop', CHECK_COPY[c.id][0], CHECK_COPY[c.id][1](pl)));
    });
    hero.appendChild(h('div', { class: 'stack tight' },
      h('span', { class: 'eyebrow' }, pl.riskName + ' · ' + years(p.horizon) + (pl.buy.held > 0 ? ' · ' + money(pl.buy.held) + ' already invested' : '')),
      h('h1', { class: 'hero-title' }, 'Where your next ' + money(p.amount) + ' goes'),
      h('p', { class: 'sub' }, summarySentence(pl))));

    var bar = h('div', { class: 'segbar', role: 'img', 'aria-label': 'Target mix: ' + pl.rows.filter(function (r) { return r.target > 0; }).map(function (r) { return r.label + ' ' + r.target + '%'; }).join(', ') });
    pl.rows.forEach(function (r) {
      if (r.target > 0) bar.appendChild(h('div', { class: 'seg', title: r.label + ' ' + r.target + '%', style: { 'flex-grow': String(r.target), 'flex-basis': '0', background: COLOR[r.key] } }));
    });
    hero.appendChild(bar);

    var listEl = h('div', { class: 'alloc' });
    pl.rows.forEach(function (r) {
      var tone = r.stance === 'over' || r.stance === 'extra' ? 'pos' : r.stance === 'under' || r.stance === 'less' ? 'neg' : '';
      var ico = tone === 'pos' ? 'up' : tone === 'neg' ? 'down' : 'flat';
      var det = h('details', { class: 'alloc-item' + (r.target === 0 ? ' zero' : ''), id: 'row-' + r.key, open: !!S.open[r.key] },
        h('summary', null,
          h('span', { class: 'swatch', style: { background: COLOR[r.key] } }),
          h('span', { class: 'alloc-name' }, r.label, pl.k > 0 || r.stance === 'none' ? chip(r.stanceText, tone, r.stance === 'none' ? null : ico) : null),
          h('span', { class: 'alloc-pct num' }, r.target + '%'),
          h('span', { class: 'alloc-amt num' }, money(Math.round(r.amount))),
          h('span', { class: 'caret', 'aria-hidden': 'true' }, '▶'),
          h('span', { class: 'alloc-why' }, rowWhy(r, pl))),
        rowDetail(r, pl));
      det.addEventListener('toggle', function () { S.open[r.key] = det.open; });
      listEl.appendChild(det);
    });
    hero.appendChild(listEl);
    hero.appendChild(h('p', { class: 'note' }, (pl.buy.held > 0 ? 'Percentages are the target for your whole portfolio; dollar figures split this deposit to move you toward it. ' : '') + 'Select a row to see every reading behind it.'));

    // pacing
    var pc = pl.pacing, vix = S.snap && S.snap.macro && isNum(S.snap.macro.vix) ? S.snap.macro.vix.toFixed(0) : null;
    var paceCopy = {
      evidence: ['Put it in all at once', 'Since 1976, investing a lump sum straight away has beaten spreading it out about 68% of the time, because markets rise more often than they fall. Spreading out mainly helps if an early drop would make you abandon the plan.'],
      small: ['Put it in all at once', 'At this size, splitting into smaller buys adds effort without much protection.'],
      cash: ['Nothing to time', 'Everything in this plan sits in cash, which you can add at any moment.'],
      nervous: ['Spread it over ' + pc.steps + ' monthly buys', 'You said a big drop would be hard to sit through. Buying in equal monthly steps gives up a little return on average, but makes a bad first month far easier to live with. Put the cash part in today.'],
      stressed: ['Spread it over ' + pc.steps + ' monthly buys', 'Markets are under stress' + (vix ? ' (the VIX is at ' + vix + ')' : '') + '. Stepping in over a few months lowers the odds of buying everything just before another leg down. Put the cash part in today.'],
      'stressed-nervous': ['Spread it over ' + pc.steps + ' monthly buys', 'Markets are under stress and you said a big drop would be hard to sit through. Go slowly: equal monthly steps, with the cash part in today.']
    }[pc.why];
    rest.appendChild(callout('info', paceCopy[0], paceCopy[1]));
    var cRow = pl.rows.filter(function (r) { return r.key === 'crypto'; })[0];
    if (cRow.amount >= 60) rest.appendChild(callout('info', 'Buy the crypto slice in pieces', 'Crypto swings three to four times as much as stocks. Split the ' + money(Math.round(cRow.amount)) + ' into at least three buys, a week or more apart.'));
    pl.checks.filter(function (c) { return c.level !== 'stop'; }).forEach(function (c) {
      rest.appendChild(callout(c.level === 'warn' ? 'warn' : 'info', CHECK_COPY[c.id][0], CHECK_COPY[c.id][1](pl)));
    });
    pl.buy.trims.forEach(function (t) {
      rest.appendChild(callout('warn', E.LABELS[t.key] + ' will still be ' + Math.round(t.over) + ' points over target', 'Even after this deposit it makes up ' + Math.round(t.share) + '% of your holdings against a ' + t.target + '% target. Selling to rebalance can trigger tax, so many people fix this with future deposits instead.'));
    });

    // stress test
    var total = pl.buy.total || p.amount, lossPct = pl.stress.pct / 100;
    rest.appendChild(h('section', { class: 'card stack' },
      h('h2', null, 'If the worst happened again'),
      h('div', { class: 'tiles' },
        tile('Fall in a repeat of each part’s worst slide', pct(lossPct, 0), 'all at the same time', ''),
        tile(money(total) + ' would become about', money(Math.round(total * (1 + lossPct))), 'before any recovery', ''),
        tile('Share in stocks and crypto', (pl.target.us + pl.target.intl + pl.target.crypto) + '%', 'limit for your timeline: ' + pl.base.growthCap + '%', '')),
      h('p', { class: 'note' }, 'Uses the deepest falls since 2000: US stocks ' + MINUS + '51%, international stocks ' + MINUS + '57%, crypto ' + MINUS + '80%, gold ' + MINUS + '45%, bonds ' + MINUS + '17%. They did not all happen together, so this is a deliberately harsh test. If the number would make you sell, choose a more cautious answer above.')));

    var hint = $('style-hint');
    if (hint) hint.textContent = { steady: 'You hold your baseline mix whatever the market does. For most long-term investors this is hard to beat.', balanced: 'Signals can move each part up or down by as much as 35% of its size.', active: 'Signals can move each part by as much as 70% of its size. Expect more changes, and more of them to be wrong.' }[p.style];
  }

  function buildPlan() {
    var root = clear($('view-plan'));
    root.appendChild(h('div', { class: 'plan-grid' },
      h('section', { class: 'card plan-hero stack', id: 'plan-hero' }),
      buildControls(),
      h('div', { class: 'plan-rest stack', id: 'plan-rest' })));
    renderPlan();
  }

  // ------------------------------------------------------------------ markets
  function renderMarkets() {
    dropObservers('markets');
    var root = clear($('view-markets'));
    roBucket = ROS.markets;
    var s = S.snap;
    if (!s) { roBucket = null; root.appendChild(emptyState('Prices, yields and the risk dial appear here once market data has loaded.')); return; }
    var m = s.macro || {}, rg = s.regime || {};

    var parts = h('div', { class: 'parts' }, (rg.parts || []).map(function (p) {
      return h('div', { class: 'part' }, h('span', { class: 'part-label' }, str(p.label, 60)), dv(p.score), h('span', { class: 'part-text' }, str(p.text, 260)));
    }));
    root.appendChild(card('Risk conditions', 'Four gauges that have tended to turn before trouble does: credit markets, expected volatility, how many sectors are rising, and the yield curve.',
      h('div', { class: 'dial-wrap' }, h('div', { class: 'stack tight' }, dial(rg.score), h('div', { class: 'dial-read', style: { 'text-align': 'center' } }, scoreWord(rg.score))), parts)));

    var f = S.brief && S.brief.facts || {};
    var tiles = h('div', { class: 'tiles' });
    if (f.fed && isNum(f.fed.lo) && isNum(f.fed.hi)) tiles.appendChild(tile('Fed policy rate', f.fed.lo.toFixed(2) + '–' + f.fed.hi.toFixed(2) + '%', str(f.fed.stance, 30) + (f.fed.next ? ' · next decision ' + dateShort(f.fed.next) : '')));
    if (isNum(m.y3m)) tiles.appendChild(tile('3-month T-bill', m.y3m.toFixed(2) + '%', isNum(m.realCash) ? signedNum(m.realCash, 1) + ' pts after inflation' : ''));
    if (isNum(m.y10y)) tiles.appendChild(tile('10-year Treasury', m.y10y.toFixed(2) + '%', isNum(m.y10yChg3m) ? signedNum(m.y10yChg3m, 2) + ' pts in 3 months' : ''));
    if (isNum(m.curve)) tiles.appendChild(tile('Yield curve (10y less 3m)', signedNum(m.curve, 2) + ' pts', m.curve < 0 ? 'inverted' : 'normal slope'));
    if (isNum(m.cpi)) tiles.appendChild(tile('Inflation, 12 months', m.cpi.toFixed(1) + '%', (m.cpiAsOf ? dateShortMonth(m.cpiAsOf) : '') + (isNum(m.cpi3mAgo) ? ' · was ' + m.cpi3mAgo.toFixed(1) + '% 3 months before' : '')));
    if (f.jobs && isNum(f.jobs.unemployment)) tiles.appendChild(tile('Unemployment', f.jobs.unemployment.toFixed(1) + '%', str(f.jobs.period, 30)));
    if (isNum(m.vix)) tiles.appendChild(tile('VIX', m.vix.toFixed(1), isNum(m.vixAvg1y) ? '1-year average ' + m.vixAvg1y.toFixed(1) : ''));
    if (isNum(m.dxy)) tiles.appendChild(tile('US dollar index', m.dxy.toFixed(1), isNum(m.dxyVs200) ? pct(m.dxyVs200) + ' vs 200-day average' : ''));
    if (isNum(m.cape)) tiles.appendChild(tile('Shiller P/E (US stocks)', m.cape.toFixed(1), isNum(m.capePct) ? 'higher than ' + Math.round(m.capePct) + '% of history' : ''));
    if (isNum(m.erp)) tiles.appendChild(tile('Stock earnings yield less 10-year', signedNum(m.erp, 1) + ' pts', m.erp < 0 ? 'bonds pay more than stocks earn' : 'stocks earn more than bonds pay'));
    root.appendChild(h('section', { class: 'stack' }, h('h2', { class: 'section-title' }, 'Rates, inflation and valuation'), tiles));

    var charts = h('div', { class: 'grid-3' });
    E.SLEEVES.forEach(function (k) {
      var ch = s.charts && s.charts[k], a = s.assets && s.assets[ch && ch.sym];
      if (!ch || !Array.isArray(ch.px)) return;
      var vs = a && a.vs200;
      var side = k === 'cash' ? (a && isNum(a.ret12m) ? pct(a.ret12m) + ' in a year' : '') : (isNum(vs) ? pct(Math.abs(vs), 1, false) + (vs >= 0 ? ' above' : ' below') + ' average' : '');
      charts.appendChild(h('div', { class: 'stack tight' },
        h('div', { class: 'mini-head' }, h('h3', null, h('span', { class: 'swatch', style: { background: COLOR[k] } }), k === 'crypto' ? 'Crypto (Bitcoin)' : E.LABELS[k]),
          h('span', { class: 'num' }, side)),
        trendChart(k, ch)));
    });
    root.appendChild(card('One year against the 200-day average', 'A price above its long-run average is in an uptrend; below it, a downtrend. Change is measured from a year ago, with dividends and interest included.',
      h('div', { class: 'legend' }, h('span', null, h('i', { style: { background: 'var(--ink-2)', height: '2px' } }), 'Price'), h('span', null, h('i', { style: { background: 'var(--muted)', height: '1.5px' } }), '200-day average')),
      charts));

    var sectors = (s.sectors || []).map(function (k) { return s.assets[k] && isNum(s.assets[k].ret3m) ? { name: s.assets[k].name, value: s.assets[k].ret3m } : null; }).filter(Boolean)
      .sort(function (a, b) { return b.value - a.value; });
    if (sectors.length) root.appendChild(card('US sectors, last 3 months', 'Which parts of the stock market are leading and lagging.', rankBars(sectors)));

    var groups = [['Stocks', ['SPY', 'QQQ', 'IWM', 'RSP', 'VXUS', 'VEA', 'VWO']], ['Bonds and cash', ['BND', 'SHY', 'IEF', 'TLT', 'TIP', 'LQD', 'HYG', 'SGOV']],
      ['Real assets', ['IAU', 'CL=F', 'DBC', 'VNQ']], ['Crypto', ['BTC-USD', 'ETH-USD', 'SOL-USD']], ['Currencies', ['DX-Y.NYB', 'EURUSD=X', 'JPY=X']]];
    var tb = h('tbody');
    groups.forEach(function (g) {
      var rows = g[1].filter(function (k) { return s.assets[k]; });
      if (!rows.length) return;
      tb.appendChild(h('tr', { class: 'group' }, h('th', { colspan: '8', scope: 'colgroup' }, g[0])));
      rows.forEach(function (k) {
        var a = s.assets[k];
        var td = function (x) { return h('td', { class: 'num ' + dirClass(x) }, pct(x)); };
        tb.appendChild(h('tr', null, h('th', { scope: 'row' }, str(a.name, 40), h('span', { class: 'sym' }, k.replace('=X', '').replace('=F', '').replace('-USD', '').replace('.NYB', ''))),
          h('td', { class: 'num' }, a.group === 'fx' && a.px < 10 ? nf(a.px, 4) : price(a.px)), td(a.chg1d), td(a.ret1m), td(a.ret3m), td(a.ret12m), td(a.vs200), h('td', null, sparkline(a.spark))));
      });
    });
    root.appendChild(card('Prices', null,
      h('div', { class: 'table-scroll' }, h('table', null,
        h('thead', null, h('tr', null, ['Asset', 'Price', 'Today', '1 month', '3 months', '12 months', 'vs 200-day', '3-month path'].map(function (t) { return h('th', { scope: 'col' }, t); }))), tb)),
      h('p', { class: 'note' }, 'Prices from Yahoo Finance, fetched ' + dateTime(s.generatedAt) + '. Fund returns include dividends where available.')));
    roBucket = null;
  }
  function dateShortMonth(ym) {
    var t = parseTime(ym + '-15T12:00:00Z');
    return t === null ? ym : new Date(t).toLocaleDateString('en-US', { month: 'short', year: 'numeric', timeZone: 'UTC' });
  }

  // ------------------------------------------------------------------- crypto
  function renderCrypto() {
    dropObservers('crypto');
    var root = clear($('view-crypto'));
    roBucket = ROS.crypto;
    var s = S.snap, c = s && s.crypto;
    if (!c || !c.btc) { roBucket = null; root.appendChild(emptyState('Bitcoin, Ether, sentiment and liquidity readings appear here once market data has loaded.')); return; }
    var b = c.btc, e = c.eth || {};
    var sl = s.sleeves && s.sleeves.crypto;
    var tiles = h('div', { class: 'tiles' },
      tile('Bitcoin', '$' + price(c.spot && isNum(c.spot.btc) ? c.spot.btc : b.px), pct(b.chg1d) + ' today', dirClass(b.chg1d)),
      tile('Ether', '$' + price(c.spot && isNum(c.spot.eth) ? c.spot.eth : e.px), pct(e.chg1d) + ' today', dirClass(e.chg1d)),
      isNum(b.fromAth) ? tile('Bitcoin from its record', pct(b.fromAth, 0), isNum(b.ath) ? 'record $' + price(b.ath) : '') : null,
      isNum(c.mcap) ? tile('All crypto, market value', moneyBig(c.mcap), isNum(c.mcapChg24h) ? pct(c.mcapChg24h) + ' in 24 hours' : '') : null,
      isNum(c.btcDom) ? tile('Bitcoin share of crypto', c.btcDom.toFixed(1) + '%', isNum(c.ethDom) ? 'Ether ' + c.ethDom.toFixed(1) + '%' : '') : null);
    root.appendChild(tiles);

    var left = h('section', { class: 'card stack' }, h('div', { class: 'row' }, h('h2', { class: 'grow' }, 'Where the model stands on crypto'), sl ? scoreChip(sl.score) : null));
    var cparts = h('div', { class: 'parts' }, ((sl && sl.parts) || []).map(function (p) {
      return h('div', { class: 'part' }, h('span', { class: 'part-label' }, str(p.label, 60)), dv(p.score), h('span', { class: 'part-text' }, str(p.text, 260)));
    }));
    var ev = S.brief && E.briefIsFresh(S.brief, Date.now()) && S.brief.sleeveScores && S.brief.sleeveScores.crypto;
    if (ev && isNum(ev.score)) cparts.appendChild(h('div', { class: 'part' }, h('span', { class: 'part-label' }, 'News and events'), dv(ev.score), h('span', { class: 'part-text' }, str(ev.why, 300))));
    if (cparts.firstChild) left.appendChild(cparts); else left.appendChild(h('p', { class: 'empty' }, 'No reading yet.'));
    var right = h('section', { class: 'card stack' });
    if (s.charts && s.charts.crypto) {
      right.appendChild(h('div', { class: 'mini-head' }, h('h2', null, 'Bitcoin, one year'), h('span', { class: 'num' }, isNum(b.vs200) ? pct(Math.abs(b.vs200), 1, false) + (b.vs200 >= 0 ? ' above' : ' below') + ' its 200-day average' : '')));
      right.appendChild(h('div', { class: 'legend' }, h('span', null, h('i', { style: { background: COLOR.crypto } }), 'Price'), h('span', null, h('i', { style: { background: 'var(--muted)' } }), '200-day average')));
      right.appendChild(trendChart('crypto', s.charts.crypto, 170));
    }
    root.appendChild(h('div', { class: 'grid-2' }, left, right));

    var trio = h('div', { class: 'grid-3' });
    if (c.fng && isNum(c.fng.now)) {
      var meter = h('div', { class: 'meter', role: 'img', 'aria-label': 'Fear and Greed Index ' + c.fng.now + ' out of 100' },
        h('s', { style: { left: '25%' } }), h('s', { style: { left: '50%' } }), h('s', { style: { left: '75%' } }), h('b', { style: { left: Math.max(1, Math.min(99, c.fng.now)) + '%' } }));
      trio.appendChild(card('Fear and Greed', null,
        h('div', { class: 'row' }, h('span', { class: 'tile-value' }, String(c.fng.now)), h('span', { class: 'sub' }, str(c.fng.label, 30) + (isNum(c.fng.avg30) ? ' · 30-day average ' + Math.round(c.fng.avg30) : ''))),
        h('div', null, meter, h('div', { class: 'meter-scale' }, h('span', null, 'Extreme fear'), h('span', null, 'Neutral'), h('span', null, 'Extreme greed'))),
        h('p', { class: 'note' }, 'A crowd-mood index from 0 to 100. Readings under about 20 or over 80 have tended to come before reversals. In between it says little.')));
    }
    if (c.stables && isNum(c.stables.usd)) {
      trio.appendChild(card('Stablecoin supply', null,
        h('div', { class: 'row' }, h('span', { class: 'tile-value' }, moneyBig(c.stables.usd)), h('span', { class: 'sub num ' + dirClass(c.stables.chg30) }, pct(c.stables.chg30) + ' in 30 days')),
        Array.isArray(c.stables.trail) ? lineChart({ height: 110, series: [{ name: 'Supply', color: COLOR.crypto, values: c.stables.trail }], tick: function (v) { return '$' + Math.round(v) + 'B'; }, fmt: function (v) { return '$' + nf(v, 0) + 'B'; }, xLabels: ['1 year ago', 'Now'], label: 'Stablecoin supply over one year' }) : null,
        h('p', { class: 'note' }, 'Dollars parked in crypto, waiting to buy. Growth means money is arriving; shrinkage means it is leaving.')));
    }
    var cyc = h('dl', { class: 'stack tight' });
    function kv(k, v) { cyc.appendChild(h('div', { class: 'row' }, h('dt', { class: 'grow sub' }, k), h('dd', { class: 'num', style: { 'font-weight': '650' } }, v))); }
    if (c.halving && isNum(c.halving.monthsSince)) kv('Months since the last halving', Math.round(c.halving.monthsSince));
    if (isNum(b.vs200w)) kv('Bitcoin vs its 200-week average', pct(b.vs200w, 0));
    if (isNum(b.ret12m)) kv('Bitcoin, 12 months', pct(b.ret12m, 0));
    if (isNum(b.vol60)) kv('Bitcoin yearly swing (volatility)', pct(b.vol60, 0, false));
    if (c.ethBtc && isNum(c.ethBtc.chg90)) kv('Ether vs Bitcoin, 90 days', pct(c.ethBtc.chg90, 0));
    trio.appendChild(card('Cycle context', null, cyc,
      h('p', { class: 'note' }, 'Past cycles peaked 12 to 18 months after a halving and then fell hard. That is three cycles of history, which is too few to rely on. The 200-week average has marked the low area of earlier bear markets.')));
    root.appendChild(trio);

    var coins = (c.top || []).filter(function (x) { return !x.stable; }).slice(0, 10);
    if (coins.length) {
      var tb = h('tbody', null, coins.map(function (x) {
        var td = function (v) { return h('td', { class: 'num ' + dirClass(v) }, pct(v)); };
        return h('tr', null, h('th', { scope: 'row' }, str(x.name, 24), h('span', { class: 'sym' }, str(x.sym, 10))), h('td', { class: 'num' }, '$' + price(x.px)),
          h('td', { class: 'num' }, moneyBig(x.mcap)), td(x.d1), td(x.d7), td(x.d30), td(x.y1), h('td', { class: 'num ' + dirClass(x.fromAth) }, pct(x.fromAth, 0)));
      }));
      root.appendChild(card('Largest coins', 'Shown for context. The plan itself sticks to Bitcoin and Ether: smaller coins have much shorter records and far deeper falls.',
        h('div', { class: 'table-scroll' }, h('table', null, h('thead', null, h('tr', null, ['Coin', 'Price', 'Market value', '24 hours', '7 days', '30 days', '1 year', 'From record'].map(function (t) { return h('th', { scope: 'col' }, t); }))), tb)),
        h('p', { class: 'note' }, 'Market data from CoinGecko, Coinbase, alternative.me and DefiLlama.')));
    }
    root.appendChild(card('Ground rules the plan follows for crypto', null, h('ul', { class: 'bullets' },
      h('li', null, 'It never exceeds the ceiling you set, and it is left out entirely for money needed within three years.'),
      h('li', null, 'Only invest an amount you could watch fall 80% without changing your life. That has happened three times.'),
      h('li', null, 'Crypto pays no earnings or interest, so its price depends on demand alone. That is why trend and money flows carry most of the weight here.'),
      h('li', null, 'Keep coins on a large regulated platform or in a spot fund. The record $6.3 billion exchange theft in October 2026 is a reminder of why that matters.'))));
    roBucket = null;
  }

  // ------------------------------------------------------------------- events
  function impactChips(impact) {
    var out = [];
    E.RISKY.forEach(function (k) {
      var v = impact && impact[k];
      if (!isNum(v) || v === 0) return;
      out.push(chip(E.LABELS[k] + (Math.abs(v) >= 2 ? ' (strong)' : ''), v > 0 ? 'pos' : 'neg', v > 0 ? 'up' : 'down'));
    });
    return out;
  }
  function renderEvents() {
    var root = clear($('view-events'));
    var b = S.brief, s = S.snap;
    if (!b && !(s && s.headlines && s.headlines.length)) { root.appendChild(emptyState('A plain-English read of what is moving markets appears here after the first news brief is written.')); return; }
    if (b) {
      var fresh = E.briefIsFresh(b, Date.now());
      root.appendChild(h('section', { class: 'card stack' },
        h('span', { class: 'eyebrow' }, 'What is moving markets · ' + dateTime(b.generatedAt)),
        h('p', { class: 'lede' }, str(b.headline, 400)),
        h('p', { class: 'prose' }, str(b.summary, 1500)),
        fresh ? null : h('p', { class: 'note' }, 'This brief is more than four days old, so it no longer moves the plan.')));

      var f = b.facts || {}, tiles = h('div', { class: 'tiles' });
      if (f.fed && isNum(f.fed.lo) && isNum(f.fed.hi)) tiles.appendChild(tile('Fed policy rate', f.fed.lo.toFixed(2) + '–' + f.fed.hi.toFixed(2) + '%', str(f.fed.odds, 120)));
      if (f.cpi && isNum(f.cpi.mom)) tiles.appendChild(tile('Consumer prices, ' + str(f.cpi.period, 20), signedNum(f.cpi.mom, 1) + '% in the month', isNum(f.cpi.coreMom) ? 'core ' + signedNum(f.cpi.coreMom, 1) + '%' + (f.cpi.lastYoy && isNum(f.cpi.lastYoy.value) ? ' · ' + f.cpi.lastYoy.value.toFixed(1) + '% over 12 months (' + str(f.cpi.lastYoy.period, 20) + ')' : '') : ''));
      if (f.jobs && isNum(f.jobs.payrolls)) tiles.appendChild(tile('Jobs added, ' + str(f.jobs.period, 20), (f.jobs.payrolls >= 0 ? '+' : MINUS) + nf(Math.abs(f.jobs.payrolls), 0), isNum(f.jobs.unemployment) ? 'unemployment ' + f.jobs.unemployment.toFixed(1) + '%' : ''));
      if (f.earnings && isNum(f.earnings.growth)) tiles.appendChild(tile('S&P 500 profits, ' + str(f.earnings.period, 12), signedNum(f.earnings.growth, 1) + '%', isNum(f.earnings.beat) ? f.earnings.beat + '% of companies beat forecasts' : ''));
      if (tiles.firstChild) root.appendChild(tiles);

      var evs = Array.isArray(b.events) ? b.events.slice(0, 12) : [];
      if (evs.length) {
        var box = h('section', { class: 'card' }, h('h2', { style: { 'margin-bottom': '8px' } }, 'The stories that matter, and what they mean for your money'));
        evs.forEach(function (ev) {
          var chips = impactChips(ev.impact);
          box.appendChild(h('article', { class: 'event' },
            h('div', { class: 'event-date' }, dateShort(str(ev.when, 30))),
            h('div', { class: 'event-body' },
              h('h3', null, str(ev.title, 200)),
              h('p', null, str(ev.what, 900)),
              h('p', { class: 'why' }, h('b', null, 'Why it matters: '), str(ev.why, 700)),
              chips.length ? h('div', { class: 'row' }, h('span', { class: 'note' }, 'Pressure on'), chips) : h('div', { class: 'row' }, h('span', { class: 'note' }, 'No clear push on any part of the plan')),
              Array.isArray(ev.sources) && ev.sources.length ? h('div', { class: 'src' }, ev.sources.slice(0, 4).map(function (so) { return link(str(so.title, 90), so.url); })) : null)));
        });
        root.appendChild(box);
      }
      var two = h('div', { class: 'grid-2' });
      if (Array.isArray(b.calendar) && b.calendar.length) {
        two.appendChild(card('Dates to know', null, h('div', null, b.calendar.slice(0, 10).map(function (c) {
          var risk = str(c.risk, 10);
          return h('div', { class: 'cal' }, h('span', { class: 'cal-date num' }, dateShort(str(c.date, 12))),
            h('span', { class: 'row' }, h('b', { class: 'grow' }, str(c.label, 120)), risk === 'high' ? chip('High stakes', 'warn', 'stop') : null),
            h('p', null, str(c.note, 300)));
        }))));
      }
      if (Array.isArray(b.watch) && b.watch.length) {
        two.appendChild(card('What would change this read', null, h('ul', { class: 'bullets' }, b.watch.slice(0, 8).map(function (w) { return h('li', null, str(w, 400)); }))));
      }
      if (two.firstChild) root.appendChild(two);
    }
    if (s && Array.isArray(s.headlines) && s.headlines.length) {
      root.appendChild(card('Latest headlines', 'The raw feed from the last refresh, newest first. Links open the original story.',
        h('ul', { class: 'wire' }, s.headlines.slice(0, 20).map(function (x) {
          return h('li', null, link(str(x.title, 220), x.url), h('span', null, str(x.src, 60) + ' · ' + ago(x.t)));
        }))));
    }
    if (b) root.appendChild(h('p', { class: 'note' }, 'The brief is written by Claude from news searches and the headline feed, then scored against each part of the plan. It is a judgment, and it can be wrong.'));
  }

  // ---------------------------------------------------------------------- ask
  var ASK_SUGGEST = ['Explain my plan like I’m new to investing', 'Why is the plan holding less gold and fewer bonds right now?', 'What is the single biggest risk to my plan this month?', 'Is now a bad time to buy Bitcoin?', 'What would make you more positive on stocks?'];
  function askContext() {
    var pl = currentPlan(), s = S.snap, b = S.brief, L = [];
    L.push('PROFILE: investing ' + money(pl.profile.amount) + ', needs the money in ' + years(pl.profile.horizon) + ', risk answer ' + pl.profile.risk + '/5 (' + pl.riskName + '), crypto ceiling ' + E.CRYPTO_CAP[pl.profile.crypto] + '%, signal strength "' + pl.profile.style + '", emergency fund: ' + (pl.profile.efund ? 'yes' : 'no') + ', high-interest debt: ' + (pl.profile.debt ? 'yes' : 'no') + '.');
    L.push('PLAN (baseline% -> target%, dollars of this deposit): ' + pl.rows.map(function (r) { return r.label + ' ' + r.base + '->' + r.target + '% ' + money(Math.round(r.amount)); }).join('; ') + '.');
    L.push('Stress test: ' + pct(pl.stress.pct / 100, 0) + '. Suggested pacing: ' + (pl.pacing.mode === 'now' ? 'all at once' : pl.pacing.steps + ' monthly steps') + '.');
    if (s) {
      L.push('DATA AS OF ' + s.generatedAt + '.');
      Object.keys(s.sleeves || {}).forEach(function (k) {
        var sl = s.sleeves[k];
        L.push(sl.label + ' reading ' + (isNum(sl.score) ? sl.score.toFixed(2) : 'n/a') + ' (' + sl.stance + '): ' + (sl.parts || []).map(function (p) { return p.label + ' [' + (isNum(p.score) ? p.score.toFixed(2) : 'n/a') + '] ' + p.text; }).join(' | '));
      });
      L.push('Risk conditions ' + (s.regime && isNum(s.regime.score) ? s.regime.score.toFixed(2) : 'n/a') + ': ' + ((s.regime && s.regime.parts) || []).map(function (p) { return p.text; }).join(' | '));
      L.push('MACRO: ' + JSON.stringify(s.macro || {}).slice(0, 1200));
      var c = s.crypto || {};
      if (c.btc) L.push('CRYPTO: BTC $' + c.btc.px + ' (' + pct(c.btc.fromAth, 0) + ' from record, ' + pct(c.btc.vs200) + ' vs 200-day); ETH $' + (c.eth && c.eth.px) + '; fear and greed ' + (c.fng && c.fng.now) + '; stablecoin supply 30-day change ' + pct(c.stables && c.stables.chg30) + '; BTC dominance ' + c.btcDom + '%.');
    }
    if (b) {
      L.push('NEWS BRIEF (' + b.generatedAt + '): ' + str(b.headline, 400) + ' ' + str(b.summary, 1500));
      (b.events || []).slice(0, 10).forEach(function (ev) { L.push('- ' + str(ev.title, 200) + ': ' + str(ev.what, 500) + ' Why it matters: ' + str(ev.why, 400)); });
      (b.calendar || []).slice(0, 8).forEach(function (c) { L.push('Upcoming ' + str(c.date, 12) + ': ' + str(c.label, 100)); });
    }
    return L.join('\n');
  }
  var ASK_RULES = 'You are the assistant inside Market Compass, a personal investing dashboard. Answer the question using the data below plus general, well-established investing knowledge. You cannot browse; if something is not in the data, say so. Write for a beginner: plain words, short paragraphs, no more than about 180 words unless asked for more, and define any jargon you use. Be direct about what the data says and honest about uncertainty. Never promise returns or tell the person a price will go up or down. If asked to pick individual stocks or small coins, explain briefly why the plan uses broad funds instead. Do not use markdown headings or tables.\n\n';
  var ASK_ERR = {
    not_granted: 'Asking Claude is switched off for this page.', sampling_disabled: 'Claude is not available on this account.', rate_limited: 'Too many questions at once, or you have hit a usage limit. Try again later.',
    session_expired: 'Your session has expired. Sign in to Claude again.', refused: 'Claude declined that question. Try wording it differently.', prompt_too_large: 'That conversation is too long. Start a new one.',
    empty_completion: 'No answer came back. Try a simpler question.'
  };
  function buildAsk() {
    var root = clear($('view-ask'));
    var log = h('div', { id: 'ask-log' });
    var ta = h('textarea', { id: 'ask-q', placeholder: 'Ask about your plan, a reading, or today’s news', 'aria-label': 'Your question', maxlength: '1000' });
    var send = h('button', { class: 'btn primary', type: 'submit', id: 'ask-send' }, 'Ask');
    var stop = h('button', { class: 'btn', type: 'button', id: 'ask-stop', hidden: true, onclick: function () { if (S.asking) S.asking.abort(); } }, 'Stop');
    var note = h('p', { class: 'note', id: 'ask-note' }, 'Answers come from Claude on your own account and are based on the data on this page. Each question uses a little of your Claude usage.');
    var form = h('form', { class: 'ask-box', onsubmit: function (e) { e.preventDefault(); ask(ta.value); } }, ta,
      h('div', { class: 'row' }, send, stop, h('button', { class: 'btn', type: 'button', id: 'ask-clear', hidden: true, onclick: function () { S.turns = []; clear(log); $('ask-clear').hidden = true; } }, 'New conversation')));
    ta.addEventListener('keydown', function (e) { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); ask(ta.value); } });
    root.appendChild(card('Ask about what you see', 'Claude gets your plan, every reading and the news brief, then answers in plain English.',
      h('div', { class: 'suggest' }, ASK_SUGGEST.map(function (q) { return h('button', { type: 'button', onclick: function () { ask(q); } }, q); })),
      form, note));
    root.appendChild(h('section', { class: 'card', id: 'ask-card', hidden: true }, log));
    setAskAvailability();
  }
  function setAskAvailability() {
    var send = $('ask-send');
    if (!send) return;
    var ok = !!S.caps.sample, pending = S.caps.sample === null && !S.capsSettled;
    send.disabled = !ok || !!S.asking;
    Array.prototype.forEach.call(document.querySelectorAll('.suggest button'), function (b) { b.disabled = !ok || !!S.asking; });
    if (!ok && !pending) $('ask-note').textContent = 'Asking Claude is not available in this view. Open the page in Claude while signed in to use it.';
  }
  function ask(q) {
    q = (q || '').trim();
    var sample = S.caps.sample;
    if (!q || !sample || S.asking) return;
    var log = $('ask-log');
    $('ask-card').hidden = false; $('ask-clear').hidden = false;
    $('ask-q').value = '';
    log.appendChild(h('div', { class: 'turn q' }, h('span', { class: 'who' }, 'You'), h('div', { class: 'said' }, q)));
    var said = h('div', { class: 'said' }, 'Thinking…');
    var err = h('p', { class: 'note' });
    log.appendChild(h('div', { class: 'turn a' }, h('span', { class: 'who' }, 'Claude'), said, err));
    said.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    S.turns.push({ role: 'user', content: q });
    var ctl = new AbortController();
    S.asking = ctl;
    $('ask-stop').hidden = false; setAskAvailability();
    var input = [{ role: 'user', content: ASK_RULES + askContext() }].concat(S.turns.slice(-8));
    sample(input, { cache: false, signal: ctl.signal, onText: function (u) { said.textContent = u.text; } }).then(function (res) {
      said.textContent = res.text;
      if (res.truncated) err.textContent = 'The answer was cut short. Ask for less at a time.';
      S.turns.push({ role: 'assistant', content: res.text });
    }).catch(function (e) {
      var kept = e && typeof e.text === 'string' ? e.text : '';
      said.textContent = kept;
      if (kept) S.turns.push({ role: 'assistant', content: kept }); else S.turns.pop();
      if (!e || e.code !== 'cancelled') err.textContent = (e && ASK_ERR[e.code]) || 'Something interrupted the answer. Try again.';
      else if (!kept) err.textContent = 'Stopped.';
      if (e && (e.code === 'not_granted' || e.code === 'sampling_disabled' || e.code === 'not_declared' || e.code === 'capability_disabled')) { S.caps.sample = false; }
    }).then(function () {
      S.asking = null; $('ask-stop').hidden = true; setAskAvailability();
    });
  }

  // ------------------------------------------------------------------- method
  function renderMethod() {
    var root = clear($('view-method'));
    root.appendChild(card('How the plan is built', 'Four steps, in order of how much they matter.',
      h('ol', { class: 'steps' },
        h('li', null, h('h3', null, 'First, the things that beat any investment'), h('p', null, 'Paying off high-interest debt and holding an emergency cushion come before everything else. If either is missing, the plan says so at the top.')),
        h('li', null, h('h3', null, 'Your timeline and nerve set a baseline mix'), h('p', null, 'How soon you need the money caps how much can sit in stocks and crypto: none for money needed within a year, up to 100% past 15 years. Your answer to the 30% question then picks a level from 20% to 95%. Stocks are split 65% US and 35% international, with about 5% gold as a diversifier. The rest is bonds and cash.')),
        h('li', null, h('h3', null, 'Live readings lean each part up or down'), h('p', null, 'Each part gets a reading from ' + MINUS + '1 to +1. Trend carries the most weight: price against its 200-day average, 12-month return against T-bills, the 50-day against the 200-day, and 3-month return. Stocks also weigh valuation and risk conditions; bonds weigh yield after inflation and where inflation is heading; gold weighs real interest rates and the dollar; crypto weighs money flows and crowd mood. The news brief adds a fifth of each reading.')),
        h('li', null, h('h3', null, 'Hard limits keep the leaning small'), h('p', null, 'A full reading moves a part by 35% of its size on the "a little" setting and 70% on "a lot". Whatever is trimmed waits in T-bills. Crypto never exceeds your ceiling and growth assets never exceed your timeline cap, whatever the signals say.')))));

    root.appendChild(card('Why it works this way', 'The research behind each design choice.',
      h('ul', { class: 'evidence' },
        h('li', null, h('b', null, 'Broad funds, not stock picks. '), 'From 1926 to 2016, about 4% of US stocks produced all of the market’s gain over Treasury bills, and most individual stocks did worse than bills. Owning the whole market guarantees you hold the winners. ', link('Bessembinder, Arizona State University', 'https://wpcarey.asu.edu/department-finance/faculty-research/do-stocks-outperform-treasury-bills')),
        h('li', null, h('b', null, 'Low-cost index funds. '), 'Around 90% of professionally managed US large-company funds have trailed the S&P 500 over 15 years. ', link('S&P SPIVA scorecard', 'https://www.spglobal.com/spdji/en/spiva/article/spiva-us-year-end-2021')),
        h('li', null, h('b', null, 'Small, bounded tilts. '), 'The average fund investor earns 1.1 to 1.6 points a year less than their own funds because of badly timed buying and selling. The tilts here are capped so a wrong signal costs little. ', link('Morningstar, Mind the Gap', 'https://www.morningstar.com/funds/investors-still-need-mind-gap-their-funds-returns')),
        h('li', null, h('b', null, 'Trend as the main signal. '), 'Holding an asset only while it is above its 10-month average has historically given similar returns with much shallower falls. It lags at turning points and gets whipsawed in choppy markets. ', link('Faber, A Quantitative Approach to Tactical Asset Allocation', 'https://papers.ssrn.com/sol3/papers.cfm?abstract_id=962461')),
        h('li', null, h('b', null, 'Valuation as a slow signal. '), 'The Shiller P/E explains roughly 40% of the variation in the following ten years of stock returns and almost none of the next year. So it gets a small weight and never drives the plan alone. ', link('Shiller P/E history', 'https://www.multpl.com/shiller-pe')),
        h('li', null, h('b', null, 'Lump sum by default. '), 'Investing at once beat spreading purchases out 68% of the time between 1976 and 2022. Spreading out is suggested only when markets are stressed or a fall would shake you out. ', link('Vanguard', 'https://www.vanguard.co.uk/professional/vanguard-365/financial-planning/financial-well-being/cost-averaging')),
        h('li', null, h('b', null, 'A ceiling on crypto. '), 'Bank of America, Morgan Stanley, Fidelity and BlackRock have each suggested between 1% and 5% for clients who want exposure. The plan offers 0, 2, 5 or 10% as a ceiling. ', link('Coverage of the bank guidance', 'https://finance.yahoo.com/news/bank-america-joins-jpmorgan-citi-230105379.html')),
        h('li', null, h('b', null, 'The yield curve. '), 'When 3-month bills pay more than 10-year bonds, a recession has usually followed within a year or two. ', link('New York Fed', 'https://www.newyorkfed.org/research/capital_markets/ycfaq')))));

    root.appendChild(card('What it cannot do', null, h('ul', { class: 'bullets' },
      h('li', null, 'Predict. Every reading describes what has already happened. Markets regularly do the opposite of what the signals suggest.'),
      h('li', null, 'Know your whole situation. It cannot see your taxes, income, pension, debts or what you already own unless you enter it. An adviser who can is worth more than any dashboard.'),
      h('li', null, 'Guarantee fresh data. Prices are delayed, a feed can fail, and the news brief is written by an AI that can misjudge a story. Each source below shows whether it loaded.'),
      h('li', null, 'Replace patience. Over decades, how much you save and how long you stay invested matter far more than any tilt on this page.'))));

    var s = S.snap;
    if (s && s.sources) {
      var tb = h('tbody', null, Object.keys(s.sources).map(function (k) {
        var src = s.sources[k] || {};
        return h('tr', null, h('th', { scope: 'row', style: { 'white-space': 'normal' } }, str(src.note, 120) || k),
          h('td', null, src.ok ? chip('Loaded', 'pos') : chip('Failed', 'neg', 'stop')));
      }));
      root.appendChild(card('Where the numbers come from', 'Last refresh: ' + dateTime(s.generatedAt) + '.',
        h('div', { class: 'table-scroll' }, h('table', null, h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Source'), h('th', { scope: 'col' }, 'Status'))), tb))));
    }
  }

  // ------------------------------------------------------------------ routing
  function route() {
    var v = (location.hash || '').replace('#', '');
    if (VIEWS.indexOf(v) < 0) v = 'plan';
    S.view = v;
    VIEWS.forEach(function (name) { $('view-' + name).hidden = name !== v; });
    Array.prototype.forEach.call(document.querySelectorAll('.tab'), function (t) {
      if (t.getAttribute('data-view') === v) t.setAttribute('aria-current', 'page'); else t.removeAttribute('aria-current');
    });
    try { localStorage.setItem('mc.view', v); } catch (e) { /* storage is optional */ }
  }

  function renderData() {
    renderFresh(); renderPlan(); renderMarkets(); renderCrypto(); renderEvents(); renderMethod();
  }

  // -------------------------------------------------------------- persistence
  var saveTimer = null, saving = false, saveAgain = false;
  function saveProfileSoon() {
    try { localStorage.setItem('mc.profile', JSON.stringify(S.profile)); } catch (e) { /* optional */ }
    if (!S.caps.db || !S.uid || S.profileReadOnly) return;
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveProfile, 900);
  }
  function saveProfile() {
    if (saving) { saveAgain = true; return; }
    saving = true;
    S.caps.db.doc('data/users/' + S.uid + '/profile').set(JSON.parse(JSON.stringify(S.profile))).then(function () {
      var n = $('save-note'); if (n) n.textContent = 'Your answers are saved privately to your account.';
    }).catch(function (e) {
      if (e && e.code === 'invalid_argument') S.profileReadOnly = true;
    }).then(function () { saving = false; if (saveAgain) { saveAgain = false; saveProfile(); } });
  }
  function loadLocalProfile() {
    try {
      var raw = localStorage.getItem('mc.profile');
      if (raw) S.profile = E.normalizeProfile(JSON.parse(raw));
    } catch (e) { /* optional */ }
  }

  // ------------------------------------------------------------------ refresh
  var RF_ERR = {
    needs_reauth: 'Reconnect Claude Code in Claude settings, under Connectors, then try again.',
    server_not_connected: 'This needs the Claude Code connector. Add it in Claude settings, under Connectors.',
    not_in_manifest: 'Refreshing from this page was not allowed. You can still ask Claude to refresh it in a chat.',
    blocked_by_policy: 'Your organization does not allow this page to start a refresh.',
    approval_required: 'The refresh needs your approval in Claude. Press the button again and allow it.'
  };
  function fireRefresh() {
    var mcp = S.caps.mcp;
    if (!mcp || !CFG.refreshTrigger || S.refreshState === 'starting') return;
    S.refreshState = 'starting'; S.refreshMsg = null; renderFresh();
    mcp.callTool(CFG.refreshServer, 'fire_trigger', { trigger_id: CFG.refreshTrigger }).then(function () {
      S.refreshState = 'started';
      S.refreshMsg = ['Refresh started. ', 'Claude is fetching prices and reading the news. New data usually lands within about ten minutes, and this page updates by itself.'];
      setTimeout(function () { S.refreshState = null; S.refreshMsg = null; renderFresh(); }, 12 * 60000);
    }).catch(function (e) {
      S.refreshState = null;
      S.refreshMsg = ['The refresh did not start. ', (e && RF_ERR[e.code]) || 'Try again in a minute, or ask Claude in a chat to refresh Market Compass.'];
      if (e && (e.code === 'not_in_manifest' || e.code === 'blocked_by_policy' || e.code === 'not_granted' || e.code === 'capability_disabled')) S.refreshReady = false;
    }).then(renderFresh);
  }
  function initRefresh(mcp) {
    if (!mcp || !CFG.refreshTrigger || !CFG.refreshServer) return;
    mcp.listTools(CFG.refreshServer).then(function (res) {
      var srv = (res && res.servers || []).filter(function (x) { return x.server === CFG.refreshServer; })[0];
      S.refreshReady = !!srv && (srv.tools || []).some(function (t) { return t.name === 'fire_trigger'; });
      renderFresh();
    }).catch(function () { S.refreshReady = false; });
  }

  // --------------------------------------------------------------------- boot
  function subscribe(db) {
    var timer = setTimeout(function () { if (!S.snap) { S.data = 'slow'; renderFresh(); } }, 10000);
    var onErr = function () { clearTimeout(timer); if (!S.snap) { S.data = 'off'; renderFresh(); } };
    db.doc('market/snapshot').onSnapshot(function (d) {
      if (d.exists) { S.snap = d.data(); S.data = 'live'; }
      if (!d.metadata || !d.metadata.fromCache) { clearTimeout(timer); if (!d.exists && !S.snap) S.data = 'empty'; }
      if (S.refreshState === 'started' && d.exists && ageHours(S.snap.generatedAt) < 0.5) { S.refreshState = null; S.refreshMsg = null; }
      renderData();
    }, onErr);
    db.doc('market/brief').onSnapshot(function (d) { S.brief = d.exists ? d.data() : null; renderData(); }, function () {});
  }

  function boot() {
    loadLocalProfile();
    buildPlan(); buildAsk(); renderData();
    window.addEventListener('hashchange', route);
    if (!location.hash) { try { var v = localStorage.getItem('mc.view'); if (v && VIEWS.indexOf(v) > 0) history.replaceState(null, '', '#' + v); } catch (e) { /* optional */ } }
    route();
    setInterval(renderFresh, 60000);

    var c = window.claude;
    if (!c || typeof c.use !== 'function') { S.data = 'off'; S.capsSettled = true; renderFresh(); setAskAvailability(); return; }
    c.use('db').then(function (db) {
      S.caps.db = db;
      if (!db) { S.data = 'off'; renderFresh(); return null; }
      subscribe(db);
      return c.use('user');
    }).then(function (user) {
      S.caps.user = user;
      return user && typeof user.id === 'function' ? user.id() : null;
    }).then(function (uid) {
      if (!uid || !S.caps.db) return;
      S.uid = uid;
      return S.caps.db.doc('data/users/' + uid + '/profile').get().then(function (d) {
        if (d.exists) { S.profile = E.normalizeProfile(d.data()); writeControls(); renderPlan(); }
        var n = $('save-note'); if (n) n.textContent = 'Your answers are saved privately to your account.';
      });
    }).catch(function () { /* the page works without saved answers */ });
    c.use('sample').then(function (s) { S.caps.sample = s || false; S.capsSettled = true; setAskAvailability(); }).catch(function () { S.caps.sample = false; S.capsSettled = true; setAskAvailability(); });
    c.use('mcp').then(function (m) { S.caps.mcp = m; initRefresh(m); }).catch(function () {});
  }

  if (window.claude && window.claude.hot && typeof window.claude.hot.ready === 'function') window.claude.hot.ready(boot);
  else if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
