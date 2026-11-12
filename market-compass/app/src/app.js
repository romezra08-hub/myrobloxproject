/* Market Compass page logic. Reads the snapshot and brief from the artifact's
 * data store, runs the engine for the viewer's profile, and draws everything.
 * Text that comes from the data store is always inserted as text, never markup. */
(function () {
  'use strict';
  var E = window.MCEngine;
  var CFG = window.MC_CONFIG || {};
  var VIEWS = ['plan', 'markets', 'crypto', 'events', 'ask', 'learn', 'method'];
  var MINUS = '−';
  var STALE_H = 30;            // older than this, prices are flagged as out of date
  var IGNORE_SIGNALS_D = 14;   // older than this, signals no longer move the plan
  var COLOR = { us: 'var(--c-us)', intl: 'var(--c-intl)', crypto: 'var(--c-crypto)', gold: 'var(--c-gold)', bonds: 'var(--c-bonds)', cash: 'var(--c-cash)' };
  var HOLD_WITH = {
    us: 'A total-market or S&P 500 index fund, such as VTI, VOO or FSKAX.',
    intl: 'A total international index fund, such as VXUS or IXUS.',
    crypto: 'Mostly Bitcoin, with Ether as a small share at most. A spot fund such as IBIT or FBTC (0.25% a year) avoids the risk of an exchange failing. If you hold coins directly, use a large regulated platform and keep no more there than you could afford to lose.',
    gold: 'A low-cost gold fund, such as IAU or GLDM. Think of it as insurance against disorder: over the long run it has earned about 1% a year after inflation.',
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
    return (x < 0 ? MINUS : '') + C().cur + nf(a, a > 0 && a < 100 && Math.round(a) !== a ? 2 : 0);
  }
  function moneyShort(x) {
    if (!isNum(x)) return '';
    var a = Math.abs(x);
    var cur = C().cur;
    if (a >= 1e6) return cur + nf(x / 1e6, a >= 1e7 ? 0 : 1) + 'M';
    if (a >= 1e3) return cur + nf(x / 1e3, a < 1e4 && Math.round(a) % 1000 !== 0 ? 1 : 0) + 'K';
    return cur + nf(x, 0);
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
  var ROS = { plan: [], markets: [], crypto: [] }, roBucket = null;
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
  function currentPlan() { return E.plan(S.profile, snapForEngine(), S.brief, Date.now(), planOpts()); }

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

  // ---------------------------------------------------------------- situation
  /* Country rules. Israel's figures are for tax year 2026 and come from published
     summaries of the rules, not from the Tax Authority directly. The refresh brief
     may supply a newer Bank of Israel rate and inflation figure. */
  var COUNTRIES = {
    IL: { name: 'Israel', cur: '₪', small: 1800, tiny: 90, taxYear: 2026,
      rate: 3.25, rateAsOf: 'October 2026', cpi: 1.6, cpiAsOf: 'September 2026', inflation: 2, bondSpread: 0.75,
      studyCeil: 15712, studySelfCap: 20566, studySelfDeduct: 13203, gemelCap: 83641,
      brackets: [[7010, 10], [10060, 14], [19000, 20], [25100, 31], [46690, 35], [60130, 47], [Infinity, 50]],
      creditPoint: 242, basePoints: 2.25 },
    other: { name: 'Elsewhere', cur: '$', small: 500, tiny: 25 }
  };
  function C() { return COUNTRIES[S.profile.country] || COUNTRIES.other; }
  function isIL() { return S.profile.country === 'IL'; }
  function ilFacts() {
    var c = COUNTRIES.IL;
    var f = S.brief && E.briefIsFresh(S.brief, Date.now()) && S.brief.facts && S.brief.facts.israel;
    var live = f && isNum(f.rate);
    return {
      rate: live ? f.rate : c.rate, rateAsOf: live ? dateShort(S.brief.generatedAt) : c.rateAsOf,
      cpi: f && isNum(f.cpi) ? f.cpi : c.cpi, cpiAsOf: f && isNum(f.cpi) && f.cpiPeriod ? str(f.cpiPeriod, 30) : c.cpiAsOf,
      next: f && f.next ? str(f.next, 12) : null
    };
  }
  /* What the engine needs to know about where you live: the size below which splitting a
     purchase is pointless, local yields for the steady part, and which parts have no usable
     signal. US bond readings say nothing about shekel bonds, so that part stays at baseline. */
  function planOpts() {
    if (!isIL()) return { small: COUNTRIES.other.small };
    var f = ilFacts(), c = COUNTRIES.IL;
    return { small: c.small, noSignal: ['bonds'], local: { cash: f.rate, bond: f.rate + c.bondSpread, inflation: c.inflation } };
  }
  function ilIncomeTax(monthly) {
    var c = COUNTRIES.IL, prev = 0, tax = 0, top = 0;
    c.brackets.forEach(function (b) {
      if (monthly > prev) { tax += (Math.min(monthly, b[0]) - prev) * b[1] / 100; top = b[1]; }
      prev = b[0];
    });
    var credit = c.basePoints * c.creditPoint;
    return { top: monthly > 0 ? top : 0, tax: Math.max(0, tax - credit), free: tax <= credit };
  }

  var HOLD_IL = {
    us: 'An S&P 500 tracking fund (keren mehaka, קרן מחקה) on the Tel Aviv exchange, from a manager such as Harel, KSM, Tachlit, MTF or IBI. Or an Irish-domiciled fund such as CSPX through a foreign broker. Avoid US-listed funds like VOO: from Israel a quarter or more of their dividends is withheld, and US assets above $60,000 can face US estate tax.',
    intl: 'A tracking fund on a world index outside the US. Or use one all-world fund (MSCI ACWI or FTSE All-World) for this row and the one above together. A Tel Aviv 125 fund can be part of it, but keep it modest: your job, home and pension already depend on Israel’s economy.',
    crypto: 'An Israeli Bitcoin tracking fund, available on the Tel Aviv exchange since the end of 2024, keeps it inside your ordinary account and its tax reporting. If you buy coins directly, use a licensed Israeli provider and keep every record: gains are taxed at 25%, and banks may ask where the money came from.',
    gold: 'A gold tracking fund on the Tel Aviv exchange, or an Irish-domiciled one such as SGLN or IGLN. Think of it as insurance against disorder: over the long run it has earned about 1% a year after inflation.',
    cash: 'A shekel money-market fund (keren kaspit, קרן כספית) or Makam, which follow the Bank of Israel rate. A current account usually pays nothing.'
  };

  /* The order your money should move in, built from what you entered. Each step is [title, text]. */
  function nextSteps(pl) {
    var p = pl.profile, s = p.situation, f = pl.first, c = C(), il = isIL(), steps = [];
    if (s.debt > 0) {
      if (f.costly) steps.push([f.toDebt > 0 ? 'Pay ' + money(f.toDebt) + ' off your debt' : 'Clear your ' + s.debtRate + '% debt', 'A debt at ' + s.debtRate + '% is a certain ' + s.debtRate + '% saving, more than any part of this plan can promise.' + (f.debtLeft > 0 ? ' ' + money(f.debtLeft) + ' would still be owed, so the next deposits go there too.' : ' This clears it.')]);
      else steps.push(['Your ' + s.debtRate + '% debt can wait', 'It costs less than the plan expects to earn before inflation, so paying it on schedule and investing alongside is reasonable.']);
    }
    if (s.spending > 0) {
      if (f.gapLeft + f.toSavings > 0) steps.push([f.toSavings > 0 ? 'Put ' + money(f.toSavings) + ' into your cushion' : 'Build your cushion next', 'You have about ' + (Math.round(f.monthsSaved * 10) / 10) + ' months of spending set aside and the aim is ' + f.months + (f.months === 6 ? ' (six, because your income is irregular)' : '') + '. ' + (il ? 'Keep it in a shekel money-market fund, which follows the Bank of Israel rate of ' + ilFacts().rate + '%.' : 'Keep it in savings or T-bills.') + (f.gapLeft > 0 ? ' ' + money(f.gapLeft) + ' more is needed after this.' : '')]);
      else steps.push(['Your cushion is in place', 'About ' + Math.round(f.monthsSaved) + ' months of spending is set aside. That is what lets you leave investments alone in a bad year.']);
    }
    if (il) {
      if (s.status === 'employee') {
        if (s.studyFund === 'yes') steps.push(['Keep your Keren Hishtalmut going', 'It is the strongest tax shelter in Israel: gains come out tax-free after six years. If the money will stay longer than that, choose a share-based or index-tracking track over the default.']);
        else steps.push(['Ask your employer about a Keren Hishtalmut (קרן השתלמות)', 'Where it is offered, the employer typically adds 7.5% of your salary to your own 2.5%, free of tax on salary up to ' + money(c.studyCeil) + ' a month, and gains come out tax-free after six years. Nothing in this plan beats that, so take it first.']);
        if (s.pension !== 'yes') steps.push(['Check that your pension is being paid', 'The law requires your employer to pay into a pension for you: about 6.5% of salary plus a severance share, with 6% from you. If your payslip does not show it, raise it.']);
      } else if (s.status === 'self') {
        steps.push(['Open a Keren Hishtalmut for the self-employed', 'Up to ' + money(c.studySelfCap) + ' a year grows tax-free, and up to ' + money(c.studySelfDeduct) + ' of it (4.5% of income) can be deducted. The self-employed must also pay into a pension.']);
      } else if (s.status === 'service') {
        steps.push(['Know what your discharge money can do', 'The discharge grant (ma’anak) is yours to use freely. The deposit (pikadon) is reserved for study or training, a home, a business or a wedding, and opens for any use about five years after discharge. Check your own amounts with the Fund for Discharged Soldiers.']);
      } else {
        steps.push(['Start small and make it automatic', 'With little income the habit matters more than the amount. A standing order into one tracking fund each month builds it.']);
      }
    }
    if (f.invest > 0) steps.push(['Invest ' + money(f.invest) + ' as shown above', il
      ? 'Two sensible homes in Israel. A trading account (at a bank or broker) holding tracking funds has the lowest fees and the most control. A Kupat Gemel LeHashkaa (קופת גמל להשקעה) takes up to ' + money(c.gemelCap) + ' a year and lets you switch tracks without tax, usually for a higher fee. Either works; compare the management fee before you choose.'
      : 'Use a tax-sheltered account if your country offers one, then an ordinary account holding broad index funds.']);
    else if (f.known) steps.push(['Nothing left to invest this time', 'That is the right outcome. The steps above pay more, and more surely, than anything on this page.']);
    if (il) {
      var t = s.income > 0 ? ilIncomeTax(s.income) : null;
      steps.push(['Know the tax before you sell', 'Israel takes 25% of your gain after inflation when you sell, and nothing while you hold. So rebalance with new money instead of selling.' +
        (t ? (t.free ? ' At ' + money(s.income) + ' a month your credit points cover your income tax, so you currently pay none.' : ' At ' + money(s.income) + ' a month your top income-tax rate is ' + t.top + '%.') : '') +
        (t && t.free || s.status === 'service' || s.status === 'student' ? ' With little or no salary you may be able to reclaim tax withheld on gains by filing a return. Ask the Tax Authority or an adviser; this app could not confirm the rule.' : '')]);
    }
    return steps;
  }

  // --------------------------------------------------------------------- plan
  function heldTotal(p) { return E.SLEEVES.reduce(function (a, k) { return a + (p.holdings[k] || 0); }, 0); }
  function riskQuestion(p) {
    var a = p.amount + heldTotal(p);
    if (!(a >= 100)) a = 1000;
    return 'If your ' + money(a) + ' fell to ' + money(Math.round(a * 0.7)) + ' and stayed there for three years, you would';
  }
  var STYLE_HINT = {
    steady: 'You hold your baseline mix whatever the market does. Most of the research favours this for most people.',
    balanced: 'A full reading can trim a part by 35% of its size, or add 20%. This is about as far as the evidence supports.',
    active: 'A full reading can trim a part by half, or add 25%. Expect more changes, and more of them to be wrong.'
  };

  function radioSet(name, options, current, cls) {
    var box = h('div', { class: cls });
    options.forEach(function (o) {
      var id = 'f-' + name + '-' + o[0];
      box.appendChild(h('input', { type: 'radio', name: name, id: id, value: o[0], checked: String(current) === String(o[0]) }));
      box.appendChild(h('label', { for: id }, o[1]));
    });
    return box;
  }
  function moneyField(id, label, value, hint) {
    return h('div', { class: 'field' }, h('label', { for: id }, label),
      h('div', { class: 'money' }, h('span', { 'aria-hidden': 'true' }, C().cur), h('input', { id: id, type: 'number', inputmode: 'decimal', min: '0', step: '50', value: value })),
      hint ? h('span', { class: 'hint' }, hint) : null);
  }

  function buildSituation() {
    var p = S.profile, s = p.situation, il = isIL();
    var tri = [['yes', 'Yes'], ['no', 'No'], ['unsure', 'Not sure']];
    var works = [['employee', 'Employee'], ['self', 'Self-employed'], ['service', il ? 'Army or national service' : 'Military or national service'], ['student', 'Student or not working']];
    return h('section', { class: 'card stack', id: 'situation' },
      h('h2', null, 'Your situation'),
      h('p', { class: 'hint' }, 'Optional, and round numbers are enough. With these, the plan puts your money in the right order instead of only warning you.'),
      h('fieldset', { class: 'field' }, h('legend', null, 'Where you live'), radioSet('country', [['IL', 'Israel'], ['other', 'Elsewhere']], p.country, 'seg-ctl')),
      h('div', { class: 'field' }, h('label', { for: 'f-s-status' }, 'Work'),
        h('select', { id: 'f-s-status', class: 'select' }, works.map(function (o) { return h('option', { value: o[0], selected: s.status === o[0] }, o[1]); }))),
      moneyField('f-s-income', 'Monthly income before tax', s.income || ''),
      moneyField('f-s-spending', 'Monthly spending', s.spending || ''),
      moneyField('f-s-savings', 'Savings you can reach quickly', s.savings || ''),
      h('div', { class: 'hold-grid' },
        moneyField('f-s-debt', 'Costliest debt', s.debt || ''),
        h('div', { class: 'field' }, h('label', { for: 'f-s-rate' }, 'Its yearly interest'),
          h('div', { class: 'money' }, h('input', { id: 'f-s-rate', type: 'number', inputmode: 'decimal', min: '0', max: '100', step: '0.5', value: s.debtRate || '', style: { 'padding-left': '10px' } }), h('span', { 'aria-hidden': 'true', style: { padding: '0 10px 0 2px' } }, '%')))),
      il ? h('fieldset', { class: 'field' }, h('legend', null, 'Does an employer pay into a Keren Hishtalmut for you?'), radioSet('studyFund', tri, s.studyFund, 'seg-ctl')) : null,
      il ? h('fieldset', { class: 'field' }, h('legend', null, 'Is a pension being paid in for you?'), radioSet('pension', tri, s.pension, 'seg-ctl')) : null,
      h('p', { class: 'note' }, 'Never enter account numbers, ID numbers or passwords. Nothing here needs them.'),
      h('p', { class: 'note', id: 'save-note' }, ''));
  }

  function buildControls() {
    var p = S.profile;
    var horizonOut = h('output', { for: 'f-horizon', class: 'num', id: 'f-horizon-out' }, years(p.horizon));
    var about = h('section', { class: 'card stack' },
      h('h2', null, 'About you'),
      moneyField('f-amount', 'Money to invest now', p.amount),
      moneyField('f-monthly', 'Adding each month', p.monthly || '', 'Optional. In the early years, how much you add matters more than what it earns.'),
      h('div', { class: 'field' },
        h('div', { class: 'row' }, h('label', { for: 'f-horizon', class: 'grow' }, 'When you will need it'), horizonOut),
        h('input', { id: 'f-horizon', type: 'range', min: '0', max: '40', step: '1', value: p.horizon }),
        h('span', { class: 'hint' }, 'The single biggest input. Money needed soon cannot ride out a crash.')),
      h('fieldset', { class: 'field' }, h('legend', { id: 'risk-legend' }, riskQuestion(p)),
        radioSet('risk', [[1, 'Sell everything'], [2, 'Sell some to feel safer'], [3, 'Hold, and lose sleep'], [4, 'Hold without much worry'], [5, 'Buy more']], p.risk, 'opt-list'),
        h('span', { class: 'hint' }, 'Answer for the worst day, not today. People tend to feel braver while prices are rising.')),
      h('fieldset', { class: 'field' }, h('legend', null, 'Crypto, at most'),
        radioSet('crypto', [['none', 'None'], ['small', '2%'], ['medium', '5%'], ['high', '10%']], p.crypto, 'seg-ctl'),
        h('span', { class: 'hint' }, 'A ceiling, not a target. Large banks suggest 1 to 5% for those who want any.')),
      h('fieldset', { class: 'field' }, h('legend', null, 'How much should market signals move the plan'),
        radioSet('style', [['steady', 'Not at all'], ['balanced', 'A little'], ['active', 'More']], p.style, 'seg-ctl'),
        h('span', { class: 'hint', id: 'style-hint' }, STYLE_HINT[p.style])),
      h('label', { class: 'check', for: 'f-efund', id: 'chk-efund' }, h('input', { type: 'checkbox', id: 'f-efund', checked: p.efund }), h('span', null, 'I have 3 to 6 months of spending set aside')),
      h('label', { class: 'check', for: 'f-debt', id: 'chk-debt' }, h('input', { type: 'checkbox', id: 'f-debt', checked: p.debt }), h('span', null, 'I have credit-card or other high-interest debt')),
      h('label', { class: 'check', for: 'f-unstable' }, h('input', { type: 'checkbox', id: 'f-unstable', checked: p.unstable }), h('span', null, 'My income is irregular, or rises and falls with the stock market')),
      h('details', { class: 'plain', id: 'hold-details', open: E.SLEEVES.some(function (k) { return p.holdings[k] > 0; }) },
        h('summary', null, 'Already invested? Add what you hold'),
        h('div', { class: 'stack', style: { 'margin-top': '10px' } },
          h('p', { class: 'hint note' }, 'New money then goes to whatever is furthest below target, so you rebalance by buying.'),
          h('div', { class: 'hold-grid' }, E.SLEEVES.map(function (k) { return moneyField('f-h-' + k, E.LABELS[k], p.holdings[k] || ''); })))));
    var form = h('form', { class: 'plan-controls', id: 'controls', autocomplete: 'off', onsubmit: function (e) { e.preventDefault(); } }, about, buildSituation());
    form.addEventListener('input', readControls);
    form.addEventListener('change', readControls);
    return form;
  }

  function readControls() {
    var f = $('controls');
    if (!f) return;
    var pick = function (name) { var el = f.querySelector('input[name="' + name + '"]:checked'); return el ? el.value : undefined; };
    var holdings = {}, was = S.profile.country;
    var n = function (id) { var el = $(id); return el ? Number(el.value) || 0 : 0; };
    E.SLEEVES.forEach(function (k) { holdings[k] = n('f-h-' + k); });
    S.profile = E.normalizeProfile({
      amount: $('f-amount').value === '' ? 0 : Number($('f-amount').value), monthly: n('f-monthly'),
      horizon: Number($('f-horizon').value), risk: Number(pick('risk')), crypto: pick('crypto'), style: pick('style'),
      efund: $('f-efund').checked, debt: $('f-debt').checked, unstable: $('f-unstable').checked, holdings: holdings,
      country: pick('country'),
      situation: { status: $('f-s-status').value, income: n('f-s-income'), spending: n('f-s-spending'), savings: n('f-s-savings'),
        debt: n('f-s-debt'), debtRate: n('f-s-rate'), studyFund: pick('studyFund') || S.profile.situation.studyFund, pension: pick('pension') || S.profile.situation.pension }
    });
    if (S.profile.country !== was) {          // currency and the questions asked both depend on the country
      f.replaceWith(buildControls());
      S.learnBuilt = false;
      renderData();
    } else {
      $('f-horizon-out').textContent = years(S.profile.horizon);
      $('risk-legend').textContent = riskQuestion(S.profile);
      renderPlan();
    }
    saveProfileSoon();
  }

  /* Saved answers arrive after the first paint. Rebuilding the form is simpler than setting
     every field, and it also picks up the right currency and questions for the country. */
  function writeControls() {
    var f = $('controls');
    if (f) f.replaceWith(buildControls());
  }

  function topDriver(parts, final) {
    var live = (parts || []).filter(function (p) { return isNum(p.score); });
    if (!live.length) return null;
    var same = live.filter(function (p) { return !isNum(final) || final === 0 || (p.score > 0) === (final > 0); });
    return (same.length ? same : live).slice().sort(function (a, b) { return Math.abs(b.score * b.weight) - Math.abs(a.score * a.weight); })[0];
  }

  /* How to hold each part. Bonds depend on the timeline and on whether inflation is driving markets. */
  function holdWith(key, pl) {
    if (isIL()) {
      if (key !== 'bonds') return HOLD_IL[key];
      if (pl.profile.horizon < 3) return 'Shekels, and short: Makam or a shekel money-market fund only, for money needed this soon.';
      return 'Shekel bonds, so the steady part of your money is in the currency you spend. An Israeli government bond tracking fund, with CPI-linked bonds (tzamud madad, \u05E6\u05DE\u05D5\u05D3 \u05DE\u05D3\u05D3) as the share that protects against inflation.';
    }
    if (key !== 'bonds') return HOLD_WITH[key];
    var snap = snapForEngine(), ir = snap && snap.macro && snap.macro.inflationRegime, mode = ir && ir.mode;
    if (pl.profile.horizon < 3) return 'Short-term only for money needed this soon: T-bills or a short Treasury fund, such as SGOV, SHY or BSV.';
    if (mode === 'short') return 'Inflation is driving markets right now, so keep this part short: about 40% in T-bills or short Treasuries (SGOV, SHY), about 35% in short inflation-linked bonds (VTIP, STIP), and no more than 25% in a broad bond fund (BND, AGG). Leave long-term bonds out.';
    if (mode === 'mixed') return 'Half in a broad bond fund (BND, AGG) and half in T-bills and short inflation-linked bonds (SGOV, VTIP), until inflation settles.';
    return 'A broad bond index fund, such as BND or AGG. BSV is a shorter, steadier version.' + (pl.profile.horizon >= 10 ? ' For goals a decade or more away, an inflation-linked fund such as SCHP can make up part of it.' : '');
  }

  function rowWhy(row, pl) {
    var snap = snapForEngine(), sl = snap && snap.sleeves && snap.sleeves[row.key];
    if (row.key === 'cash') {
      var y = sl && sl.parts && sl.parts[0] ? str(sl.parts[0].text, 200) : '';
      var lead = row.stance === 'extra' ? 'Holds what the signals trimmed elsewhere. ' : row.stance === 'less' ? 'Drawn on to fund stronger parts. ' : '';
      if (isIL()) { var il = ilFacts(); return lead + 'Shekel money-market funds follow the Bank of Israel rate, ' + il.rate + '%, about ' + (il.rate - il.cpi).toFixed(1) + ' points above inflation.'; }
      return lead + (y && y !== 'No reading' ? y + '.' : 'Your steady anchor.');
    }
    if (row.unread && row.target > 0) return 'Kept at its baseline. The bond readings on this page are for US bonds, and yours should be shekel bonds.';
    if (row.stance === 'none') {
      if (row.key === 'crypto') {
        if (S.profile.crypto === 'none') return 'You chose to hold none.';
        if (S.profile.risk === 1) return 'Left out: it can fall 80%, and you said a 30% fall would make you sell.';
        return 'Left out for money needed within four years: its recoveries have taken two to four.';
      }
      if (row.key === 'gold') return 'Left out for money needed within three years.';
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
    var line = 'Baseline ' + row.base + '%. Now ' + row.target + '%' +
      (moved !== 0 ? ' (' + (moved > 0 ? '+' : MINUS) + Math.abs(moved) + (Math.abs(moved) === 1 ? ' point).' : ' points).') : '.');
    if (row.target > 0) line += ' It holds ' + row.target + '% of your money and carries about ' + Math.max(0, Math.round(row.riskShare * 100)) + '% of the risk.';
    box.appendChild(h('p', { class: 'sub' }, line));
    if (row.unread) box.appendChild(h('p', { class: 'sub' }, 'No reading is applied here. The bond signals on this page are built on US bonds and US inflation, and yours should be shekel bonds, which follow the Bank of Israel. That bank was holding its rate while the US was raising, so borrowing the US reading would mislead. This part stays at its baseline.'));
    if (row.key !== 'cash' && isNum(row.score) && !row.unread) {
      box.appendChild(h('p', { class: 'sub' }, pl.lean.down > 0
        ? 'Overall reading ' + signedNum(row.score, 2) + ' on a scale of ' + MINUS + '1 to +1. At your setting, a full negative reading trims a part by ' + Math.round(pl.lean.down * 100) + '% of its size and a full positive one adds ' + Math.round(pl.lean.up * 100) + '%.'
        : 'Overall reading ' + signedNum(row.score, 2) + ' on a scale of ' + MINUS + '1 to +1. Readings are shown for information and do not move your plan.'));
    }
    if (sl && sl.parts && row.key !== 'cash' && !row.unread) {
      var parts = h('div', { class: 'parts' });
      sl.parts.forEach(function (p) {
        parts.appendChild(h('div', { class: 'part' }, h('span', { class: 'part-label' }, str(p.label, 60) + ' · ' + Math.round((p.weight || 0) * 100) + '%'), dv(p.score), h('span', { class: 'part-text' }, str(p.text, 260))));
        if (Array.isArray(p.detail)) {
          var bits = p.detail.filter(function (d) { return isNum(d.score); }).map(function (d) { return str(d.text, 120); });
          if (bits.length) parts.appendChild(h('p', { class: 'note' }, bits.join(' · ')));
        }
      });
      var ev = pl.eventsUsed && S.brief.sleeveScores && S.brief.sleeveScores[row.key];
      if (ev && isNum(ev.score)) {
        parts.appendChild(h('div', { class: 'part' }, h('span', { class: 'part-label' }, 'News'), dv(ev.score), h('span', { class: 'part-text' }, str(ev.why, 300))));
      }
      box.appendChild(parts);
      if (sl.capNote) box.appendChild(h('p', { class: 'note' }, str(sl.capNote, 200) + '.'));
      if (ev && isNum(ev.score)) {
        box.appendChild(h('p', { class: 'note' }, row.eventEffect < -0.004
          ? 'The news is gloomier than prices, so it made this reading more careful by ' + Math.abs(row.eventEffect).toFixed(2) + '. News can only ever do that: it never makes the plan bolder.'
          : 'The news is no gloomier than prices here, so it changes nothing. News can only make the plan more careful, never bolder.'));
      }
    }
    box.appendChild(h('p', { class: 'sub' }, h('b', null, 'How to hold it: '), holdWith(row.key, pl), ' Examples, not endorsements.'));
    return box;
  }

  function summarySentence(pl) {
    if (!snapForEngine()) return 'Live signals are not available right now, so this is your baseline mix.';
    if (pl.lean.down === 0) return 'This is your baseline mix. Market signals are shown for information and do not move it.';
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
    debt: ['Pay off high-interest debt before investing', function () { return 'A card charging 22% costs more than anything here can reliably earn, so clearing it is the best return available. If your employer matches pension contributions, take the full match first: that is free money. Use this plan for what is left.'; }],
    efund: ['Build a safety cushion first', function () {
      var y = S.snap && S.snap.macro && isNum(S.snap.macro.y3m) ? ' (T-bills currently pay about ' + S.snap.macro.y3m.toFixed(1) + '%)' : '';
      return 'Keep 3 to 6 months of spending in savings or T-bills' + y + ', so a surprise bill never forces you to sell investments at a bad moment. Then invest what is left.';
    }],
    short: ['Money needed within a year belongs in cash', function () { return 'US stocks have lost money in about one year in four. For money you need that soon, the plan keeps everything in savings or T-bills.'; }],
    horizon: ['Your timeline is setting the limit', function (pl) { return 'You could stomach more risk, but money needed in ' + years(pl.profile.horizon) + ' should not have more than ' + pl.base.growthCap + '% in stocks and crypto. If stocks halved, as they did twice this century, that keeps the loss to about ' + Math.round(pl.base.growthCap / 2) + '% with time left to recover.'; }],
    crypto: ['Crypto is a small slice carrying a large share of the risk', function (pl) {
      var r = pl.rows.filter(function (x) { return x.key === 'crypto'; })[0];
      return 'It is ' + r.target + '% of your money but about ' + Math.round(r.riskShare * 100) + '% of the risk in this plan. Bitcoin has fallen more than 75% four times. A lower ceiling changes your long-run prospects very little and your worst day a great deal.';
    }]
  };
  function callout(level, title, text) {
    return h('div', { class: 'callout ' + level }, icon(level === 'info' ? 'info' : 'stop'), h('h3', null, title), h('p', null, text));
  }

  function splitBar(rows, valueOf, label) {
    var bar = h('div', { class: 'segbar', role: 'img', 'aria-label': label + ': ' + rows.filter(function (r) { return valueOf(r) > 0; }).map(function (r) { return r.label + ' ' + Math.round(valueOf(r)) + '%'; }).join(', ') });
    rows.forEach(function (r) {
      var v = valueOf(r);
      if (v > 0.4) bar.appendChild(h('div', { class: 'seg', title: r.label + ' ' + Math.round(v) + '%', style: { 'flex-grow': String(v), 'flex-basis': '0', background: COLOR[r.key] } }));
    });
    return bar;
  }

  var SCENARIO_COPY = {
    crisis: ['A 2008-style financial crisis', 'October 2007 to February 2009. Bonds and gold rose and softened the fall. US stocks took about five and a half years to regain their high.'],
    inflation: ['A 2022-style inflation shock', 'Calendar 2022. Stocks and bonds fell together, which is what tends to happen when inflation is the problem.'],
    worst: ['Every part repeats its worst fall since 2000, all at once', 'Deliberately harsh. These falls did not happen together.']
  };

  function planText(pl) {
    var p = pl.profile, L = [];
    var worst = pl.stress.scenarios.filter(function (s) { return s.id === 'crisis'; })[0];
    L.push('MY INVESTING PLAN, written ' + new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }));
    L.push('');
    L.push('Goal: money I will need in about ' + years(p.horizon) + '.');
    L.push('Target mix: ' + pl.rows.filter(function (r) { return r.target > 0; }).map(function (r) { return r.label + ' ' + r.target + '%'; }).join(', ') + '.');
    if (p.monthly > 0) L.push('Every month I add ' + money(p.monthly) + ', automatically, split the same way.');
    L.push('I look once a month at most. I change something only when a part is more than 5 points, or a quarter of its own size, away from its target, and I fix it with new money before I sell anything.');
    L.push('If markets fall 30%, I do nothing. I chose this mix knowing it could lose about ' + Math.abs(Math.round(worst.pct)) + '% in a crisis like 2008.');
    if (pl.target.crypto > 0) L.push('Crypto stays at or under ' + E.CRYPTO_CAP[p.crypto] + '% of the total. If it grows past one and a half times its target, I trim it back.');
    L.push('I review the plan itself once a year, or when my life changes. Never because of a headline.');
    return L.join('\n');
  }

  function renderPlan() {
    var hero = $('plan-hero'), rest = $('plan-rest');
    if (!hero) return;
    var pl = currentPlan(), p = pl.profile;
    clear(hero); clear(rest);
    dropObservers('plan');
    roBucket = ROS.plan;

    pl.checks.filter(function (c) { return c.level === 'stop'; }).forEach(function (c) {
      hero.appendChild(callout('stop', CHECK_COPY[c.id][0], CHECK_COPY[c.id][1](pl)));
    });
    hero.appendChild(h('div', { class: 'stack tight' },
      h('span', { class: 'eyebrow' }, pl.riskName + ' · ' + years(p.horizon) + (pl.buy.held > 0 ? ' · ' + money(pl.buy.held) + ' already invested' : '')),
      h('h1', { class: 'hero-title' }, 'Where your next ' + money(p.amount) + ' goes'),
      h('p', { class: 'sub' }, summarySentence(pl))));

    var ft = pl.first;
    if (ft.known && (ft.toDebt > 0 || ft.toSavings > 0)) {
      hero.appendChild(h('div', { class: 'stack tight' },
        h('span', { class: 'eyebrow' }, 'First things first'),
        h('div', { class: 'tiles' },
          ft.toDebt > 0 ? tile('To your debt', money(Math.round(ft.toDebt)), 'at ' + p.situation.debtRate + '% a year') : null,
          ft.toSavings > 0 ? tile('To your cushion', money(Math.round(ft.toSavings)), 'aim: ' + ft.months + ' months of spending') : null,
          tile('Invested', money(Math.round(ft.invest)), ft.invest > 0 ? 'split as below' : 'next time'))));
    }
    var live = pl.rows.filter(function (r) { return r.target > 0; });
    hero.appendChild(h('div', { class: 'twobars' },
      h('span', { class: 'bar-cap' }, 'Your money'), splitBar(live, function (r) { return r.target; }, 'Where the money goes'),
      h('span', { class: 'bar-cap' }, 'Your risk'), splitBar(live, function (r) { return Math.max(0, r.riskShare * 100); }, 'Where the risk sits')));

    var listEl = h('div', { class: 'alloc' });
    pl.rows.forEach(function (r) {
      var tone = r.stance === 'over' || r.stance === 'extra' ? 'pos' : r.stance === 'under' || r.stance === 'less' ? 'neg' : '';
      var ico = tone === 'pos' ? 'up' : tone === 'neg' ? 'down' : 'flat';
      var det = h('details', { class: 'alloc-item' + (r.target === 0 ? ' zero' : ''), id: 'row-' + r.key, open: !!S.open[r.key] },
        h('summary', null,
          h('span', { class: 'swatch', style: { background: COLOR[r.key] } }),
          h('span', { class: 'alloc-name' }, r.label, pl.lean.down > 0 || r.stance === 'none' ? chip(r.stanceText, tone, r.stance === 'none' ? null : ico) : null),
          h('span', { class: 'alloc-pct num' }, r.target + '%'),
          h('span', { class: 'alloc-amt num' }, money(Math.round(r.amount))),
          h('span', { class: 'caret', 'aria-hidden': 'true' }, '▶'),
          h('span', { class: 'alloc-why' }, rowWhy(r, pl))),
        rowDetail(r, pl));
      det.addEventListener('toggle', function () { S.open[r.key] = det.open; });
      listEl.appendChild(det);
    });
    hero.appendChild(listEl);
    hero.appendChild(h('p', { class: 'note' }, 'The second bar shows where the risk sits, which is rarely where the money sits. ' + (pl.buy.held > 0 ? 'Percentages are the target for your whole portfolio; dollar figures split this deposit to move you toward it. ' : '') + 'Select a row to see every reading behind it.'));

    // ---- your next steps, in order ----
    var stepsList = (ft.known || isIL()) ? nextSteps(pl) : [];
    if (stepsList.length) {
      rest.appendChild(h('section', { class: 'card stack' },
        h('h2', null, 'Your next steps, in order'),
        h('ol', { class: 'steps' }, stepsList.map(function (st) { return h('li', null, h('h3', null, st[0]), h('p', null, st[1])); })),
        isIL() ? h('p', { class: 'note' }, 'Israeli figures are for tax year ' + C().taxYear + ' and come from published summaries of the rules, not from the Tax Authority itself. Check a figure with the Authority or a licensed adviser before acting on it.') : null));
    }

    // ---- how to put it in, and how often to look ----
    var pc = pl.pacing;
    var paceCopy = {
      evidence: ['Put it in all at once', 'Investing a lump sum straight away has beaten spreading it out about two times in three (68% in Vanguard’s study of 1976 to 2022), because markets rise more often than they fall. Waiting for a calmer moment is market timing, and it rarely pays.'],
      small: ['Put it in all at once', 'At this size, splitting into smaller buys adds effort without much protection.'],
      cash: ['Nothing to time', 'Everything in this plan sits in cash, which you can add at any moment.'],
      nervous: ['Spread it over ' + pc.steps + ' monthly buys', 'You said a fall would be hard to sit through. Set the dates now and keep to them whatever the news says: ' + pc.steps + ' equal buys, one a month, with the cash part in today. On average this gives up a little return, which is a fair price for staying the course.']
    }[pc.why];
    if (!(ft.known && ft.invest <= 0)) rest.appendChild(callout('info', paceCopy[0], paceCopy[1]));
    var sm = snapForEngine() && snapForEngine().macro;
    if (isIL() && sm && isNum(sm.usdils) && pl.target.us + pl.target.intl + pl.target.gold + pl.target.crypto > 0) {
      rest.appendChild(callout('info', 'Most of this plan is priced in dollars',
        'One dollar buys ' + C().cur + sm.usdils.toFixed(2) + ' today' + (isNum(sm.usdils2yLow) && isNum(sm.usdils2yHigh) ? ', and in the last two years it has been as low as ' + C().cur + sm.usdils2yLow.toFixed(2) + ' and as high as ' + C().cur + sm.usdils2yHigh.toFixed(2) : '') + '. When the shekel strengthens your foreign holdings are worth less in shekels, and the reverse. Over decades this has mattered far less than what you own, but over a few years it can outweigh the market itself. That is why the steady part of your plan stays in shekels.'));
    }
    if (p.monthly > 0) rest.appendChild(callout('info', 'Make the monthly ' + money(p.monthly) + ' automatic', 'Set a standing transfer for the day you are paid, split the same way as above. Investing money as soon as you have it is not timing the market. It is the habit that does most of the work.'));
    var cRow = pl.rows.filter(function (r) { return r.key === 'crypto'; })[0];
    if (cRow.amount >= 60) rest.appendChild(callout('info', 'Buy the crypto slice in pieces', 'Crypto swings three to four times as much as stocks. Split the ' + money(Math.round(cRow.amount)) + ' into at least three buys, a week or more apart.'));
    pl.checks.filter(function (c) { return c.level !== 'stop'; }).forEach(function (c) {
      rest.appendChild(callout(c.level === 'warn' ? 'warn' : 'info', CHECK_COPY[c.id][0], CHECK_COPY[c.id][1](pl)));
    });
    pl.buy.trims.forEach(function (t) {
      rest.appendChild(callout('warn', E.LABELS[t.key] + ' will still be ' + Math.round(t.over) + ' points over target', 'Even after this deposit it makes up ' + Math.round(t.share) + '% of your holdings against a ' + t.target + '% target. Selling to rebalance can trigger tax, so point future deposits elsewhere first and sell only if that is not enough.'));
    });
    rest.appendChild(callout('info', 'Look once a month at most', 'This page refreshes every weekday. Your plan should not. Act only when a part is more than 5 points, or a quarter of its own size, away from its target. In the largest study of its kind, the households that traded most earned 11.4% a year while the market made 17.9%.'));

    // ---- what it could grow to ----
    var o = pl.outlook;
    if (p.horizon >= 1 && o.start + o.monthly > 0) {
      var yrs = [], lo = [], mid = [], hi = [], paid = [];
      for (var y = 0; y <= p.horizon; y++) {
        yrs.push(y === 0 ? 'Today' : 'Year ' + y);
        lo.push(E.futureValue(o.start, o.monthly, y, o.low / 100).value);
        mid.push(E.futureValue(o.start, o.monthly, y, o.mid / 100).value);
        hi.push(E.futureValue(o.start, o.monthly, y, o.high / 100).value);
        paid.push(o.start + o.monthly * 12 * y);
      }
      var rate = function (x) { return (x < 0 ? MINUS : '') + Math.abs(x).toFixed(1) + '% a year'; };
      var ex = o.parts;
      rest.appendChild(h('section', { class: 'card stack' },
        h('h2', null, 'What this could grow to in ' + years(p.horizon)),
        h('p', { class: 'sub' }, 'In today’s money, after inflation. The estimate is built from today’s yields and prices, which point to lower returns than the last few decades delivered.'),
        h('div', { class: 'tiles' },
          tile('Cautious case', money(Math.round(o.value.low)), rate(o.low)),
          tile('Middle case', money(Math.round(o.value.mid)), rate(o.mid)),
          tile('Hopeful case', money(Math.round(o.value.high)), rate(o.high)),
          tile('You pay in', money(Math.round(o.paidIn)), o.monthly > 0 ? money(o.start) + ' now, ' + money(o.monthly) + ' a month' : 'one deposit')),
        h('div', { class: 'legend' },
          h('span', null, h('i', { style: { background: 'var(--c-us)' } }), 'Middle case'),
          h('span', null, h('i', { style: { background: 'var(--line-2)' } }), 'Cautious and hopeful cases'),
          h('span', null, h('i', { style: { background: 'var(--ink-2)' } }), 'What you paid in')),
        lineChart({ height: 180, label: 'Projected value by year in three cases, against what you paid in',
          series: [{ name: 'Middle case', color: 'var(--c-us)', values: mid }, { name: 'Hopeful case', color: 'var(--line-2)', values: hi, width: 1.5 },
            { name: 'Cautious case', color: 'var(--line-2)', values: lo, width: 1.5 }, { name: 'Paid in', color: 'var(--ink-2)', values: paid, width: 1.5 }],
          labels: yrs, xLabels: ['Today', 'Year ' + p.horizon], tick: function (v) { return moneyShort(v); }, fmt: function (v) { return money(Math.round(v)); } }),
        h('p', { class: 'note' }, 'History suggests the result lands between the cautious and hopeful cases about two times in three; the worst outcomes lie outside them. Yearly returns assumed after ' + o.inflation + '% inflation: US stocks ' + ex.us.toFixed(1) + '%, international stocks ' + ex.intl.toFixed(1) + '%, bonds ' + ex.bonds.toFixed(1) + '%, cash ' + ex.cash.toFixed(1) + '%, gold ' + ex.gold.toFixed(1) + '%, crypto 0% (it has no earnings or interest to forecast from, so the plan counts on nothing).'),
        isIL() ? h('p', { class: 'note' }, 'Bond and cash figures use the Bank of Israel rate of ' + ilFacts().rate + '%, with bonds assumed to yield ' + C().bondSpread + ' points more, and ' + o.inflation + '% inflation, the middle of the bank\u2019s target.') : null,
        h('p', { class: 'note' }, 'Cost matters as much as any of this. ' + (isIL() ? 'Tracking funds are the cheap ones; compare the management fee (dmei nihul) before you buy.' : 'The funds suggested here charge about 0.05% a year.') + ' A fund or adviser charging 1% would take about ' + Math.round(o.feeDrag * 100) + '% of the final amount on money invested today.')));
    }

    // ---- how bad could it get ----
    var total = pl.buy.total || p.amount;
    var tb = h('tbody', null, pl.stress.scenarios.map(function (sc) {
      var c = SCENARIO_COPY[sc.id];
      return h('tr', null, h('th', { scope: 'row', style: { 'white-space': 'normal' } }, c[0], h('div', { class: 'note', style: { 'font-weight': '400' } }, c[1])),
        h('td', { class: 'num ' + dirClass(sc.pct) }, pct(sc.pct / 100, 0)),
        h('td', { class: 'num' }, money(Math.round(total * (1 + sc.pct / 100)))),
        h('td', { class: 'num' }, sc.recover > 0 ? '+' + Math.round(sc.recover) + '%' : '–'));
    }));
    rest.appendChild(h('section', { class: 'card stack' },
      h('h2', null, 'How bad could it get'),
      h('div', { class: 'table-scroll' }, h('table', { class: 'scen' },
        h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'If this happened again'), h('th', { scope: 'col' }, 'This mix'), h('th', { scope: 'col' }, money(total) + ' becomes'), h('th', { scope: 'col' }, 'Gain needed to recover'))), tb)),
      h('p', { class: 'note' }, 'None of these is a floor. US stocks fell about 86% between 1929 and 1932, Japan’s market took 34 years to regain its 1989 high, and Bitcoin has fallen more than 75% four times. Crypto did not exist in 2008, so that row assumes it falls 80%. If the worst row would make you sell, choose a more cautious answer.')));

    // ---- simpler ----
    var s3 = pl.simple, tiny = pl.rows.some(function (r) { return r.target > 0 && r.amount > 0 && r.amount < C().tiny; });
    if (s3.stocks > 0) {
      rest.appendChild(h('section', { class: 'card stack' },
        h('h2', null, 'A simpler way to hold it'),
        h('p', { class: 'sub' }, 'Six parts is more than most people need. The same balance of risk fits in three funds, or in one.'),
        h('div', { class: 'tiles' },
          tile(isIL() ? 'S&P 500 tracking fund' : 'US stock index fund', s3.us + '%', isIL() ? 'keren mehaka, Tel Aviv' : 'such as VTI or FSKAX'),
          tile(isIL() ? 'World ex-US tracking fund' : 'International index fund', s3.intl + '%', isIL() ? 'or one all-world fund for both' : 'such as VXUS'),
          tile(isIL() ? (p.horizon < 3 ? 'Makam or money-market fund' : 'Shekel government bond fund') : (p.horizon < 3 ? 'Short-term bonds and cash' : 'Bond index fund'), s3.bonds + '%', isIL() ? 'in shekels' : (p.horizon < 3 ? 'such as BSV or SGOV' : 'such as BND'))),
        h('p', { class: 'note' }, (isIL()
          ? 'Simplest of all: one all-world tracking fund for the ' + s3.stocks + '% in stocks and one shekel bond fund for the rest. Tracking mutual funds in Israel usually carry no buy or sell commission, which matters at small amounts; check your bank\u2019s custody fee.'
          : 'Or one all-in-one fund with about ' + s3.stocks + '% in stocks: a target-date fund, or a fixed-mix fund (iShares offers 30, 40, 60 and 80% versions as AOK, AOM, AOR and AOA).') + ' In the research, investors who held fewer, broader funds kept more of their returns than any other group.' + (tiny ? ' Some slices above are under ' + money(C().tiny) + '. At this size, the simpler version is the practical choice.' : ''))));
    }

    // ---- one-page plan ----
    var text = planText(pl);
    var pre = h('pre', { class: 'plan-text', id: 'plan-text', tabindex: '0' }, text);
    var copied = h('span', { class: 'note', 'aria-live': 'polite' }, '');
    var btn = h('button', { class: 'btn small', type: 'button', onclick: function () {
      var done = function () { copied.textContent = 'Copied.'; };
      var fallback = function () { var r = document.createRange(); r.selectNodeContents(pre); var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r); copied.textContent = 'Selected. Copy it with your keyboard or the menu.'; };
      try { navigator.clipboard.writeText(text).then(done, fallback); } catch (e) { fallback(); }
    } }, 'Copy');
    rest.appendChild(h('section', { class: 'card stack' },
      h('div', { class: 'row' }, h('h2', { class: 'grow' }, 'Your plan on one page'), btn, copied),
      h('p', { class: 'sub' }, 'Decide what you will do in a crash while you are calm. Keep this somewhere you will see it on a bad day.'),
      pre));

    var hint = $('style-hint');
    if (hint) hint.textContent = STYLE_HINT[p.style];
    ['chk-efund', 'chk-debt'].forEach(function (id) { var el = $(id); if (el) el.hidden = ft.known; });
    roBucket = null;
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
    var ctx = Array.isArray(rg.context) && rg.context.length ? h('div', { class: 'stack tight' },
      h('span', { class: 'eyebrow' }, 'Shown, not scored'),
      h('dl', { class: 'ctx' }, rg.context.map(function (c) { return h('div', null, h('dt', null, str(c.label, 40)), h('dd', null, str(c.text, 400))); }))) : null;
    root.appendChild(card('Risk conditions', 'Four readings the research supports as warnings for stocks: credit markets, how violently prices have been moving, a jump in interest rates, and how many sectors are rising. Some famous gauges are listed underneath but left out of the score, because they have not predicted stock returns.',
      h('div', { class: 'dial-wrap' }, h('div', { class: 'stack tight' }, dial(rg.score), h('div', { class: 'dial-read', style: { 'text-align': 'center' } }, scoreWord(rg.score))), h('div', { class: 'stack' }, parts, ctx))));

    var f = S.brief && S.brief.facts || {};
    var tiles = h('div', { class: 'tiles' });
    if (f.fed && isNum(f.fed.lo) && isNum(f.fed.hi)) tiles.appendChild(tile('Fed policy rate', f.fed.lo.toFixed(2) + '–' + f.fed.hi.toFixed(2) + '%', str(f.fed.stance, 30) + (f.fed.next ? ' · next decision ' + dateShort(f.fed.next) : '')));
    if (isNum(m.y3m)) tiles.appendChild(tile('3-month T-bill', m.y3m.toFixed(2) + '%', isNum(m.realCash) ? signedNum(m.realCash, 1) + ' pts after inflation' : ''));
    if (isNum(m.y10y)) tiles.appendChild(tile('10-year Treasury', m.y10y.toFixed(2) + '%', isNum(m.y10yChg3m) ? signedNum(m.y10yChg3m, 2) + ' pts in 3 months' : ''));
    if (isNum(m.curve)) tiles.appendChild(tile('Yield curve (10y less 3m)', signedNum(m.curve, 2) + ' pts', m.curve < 0 ? 'inverted: a recession gauge' : 'normal slope'));
    if (isNum(m.cpi)) tiles.appendChild(tile('Inflation, 12 months', m.cpi.toFixed(1) + '%', (m.cpiAsOf ? dateShortMonth(m.cpiAsOf) : '') + (isNum(m.cpi3mAgo) ? ' · was ' + m.cpi3mAgo.toFixed(1) + '% 3 months before' : '')));
    if (f.jobs && isNum(f.jobs.unemployment)) tiles.appendChild(tile('Unemployment', f.jobs.unemployment.toFixed(1) + '%', str(f.jobs.period, 30)));
    if (isNum(m.vix)) tiles.appendChild(tile('VIX', m.vix.toFixed(1), isNum(m.vixAvg1y) ? '1-year average ' + m.vixAvg1y.toFixed(1) : ''));
    if (isNum(m.dxy)) tiles.appendChild(tile('US dollar index', m.dxy.toFixed(1), isNum(m.dxyVs200) ? pct(m.dxyVs200) + ' vs 200-day average' : ''));
    if (isIL()) {
      var ilf = ilFacts();
      tiles.appendChild(tile('Bank of Israel rate', ilf.rate.toFixed(2) + '%', ilf.next ? 'next decision ' + dateShort(ilf.next) : 'as of ' + ilf.rateAsOf));
      tiles.appendChild(tile('Israeli inflation, 12 months', ilf.cpi.toFixed(1) + '%', ilf.cpiAsOf + ' \u00b7 target 1 to 3%'));
      if (isNum(m.usdils)) tiles.appendChild(tile('One US dollar in shekels', '\u20AA' + m.usdils.toFixed(2), isNum(m.usdils12m) ? pct(m.usdils12m) + ' in 12 months' + (isNum(m.usdils3m) ? ', ' + pct(m.usdils3m) + ' in 3' : '') : ''));
    }
    if (isNum(m.cape)) tiles.appendChild(tile('Shiller P/E (US stocks)', m.cape.toFixed(1), isNum(m.capePct40) ? 'higher than ' + Math.round(m.capePct40) + '% of the last 40 years' : isNum(m.capePct) ? 'higher than ' + Math.round(m.capePct) + '% of history' : ''));
    if (isNum(m.stockBondCorr)) tiles.appendChild(tile('Stocks and bonds, 3 months', signedNum(m.stockBondCorr, 2), m.stockBondCorr > 0.2 ? 'moving together: bonds are not cushioning' : m.stockBondCorr < -0.2 ? 'moving opposite: bonds are cushioning' : 'moving independently'));
    root.appendChild(h('section', { class: 'stack' }, h('h2', { class: 'section-title' }, 'Rates, inflation and valuation'), tiles));

    var ir = m.inflationRegime;
    if (ir && Array.isArray(ir.tests) && ir.mode) {
      var verdict = { short: ['Yes: ' + ir.points + ' of 4 tests', 'neg', 'Inflation, not growth, is the main worry. In past inflation surges, stocks and ordinary bonds lost together while T-bills and short inflation-linked bonds held up. The plan therefore says to hold the bond part short. Some ordinary bonds stay, because a recession would lift them.'],
        mixed: ['Partly: ' + ir.points + ' of 4 tests', 'warn', 'The picture is mixed. The plan says to hold half the bond part in T-bills and short inflation-linked bonds until it clears.'],
        normal: ['No: ' + ir.points + ' of 4 tests', 'pos', 'Growth, not inflation, is the main driver, which is when ordinary bonds do their job of cushioning stock falls. The plan holds a broad bond fund.'] }[ir.mode];
      var ilNote = { short: 'US inflation, not growth, is the main worry in American markets. It reaches you through stock prices and the dollar, not through your bonds.', mixed: 'The US picture is mixed. It reaches you through stock prices and the dollar, not through your bonds.', normal: 'Growth, not inflation, is driving American markets.' }[ir.mode];
      root.appendChild(card(isIL() ? 'Is inflation driving US markets?' : 'Is inflation driving markets?',
        isIL() ? 'These tests use US data and decide nothing in your plan. Your bond part is in shekels, and Israeli inflation is ' + ilFacts().cpi + '%.' : 'This decides how the bond part of your plan should be held.',
        h('div', { class: 'row' }, chip(verdict[0], verdict[1], verdict[1] === 'neg' ? 'stop' : null)),
        h('p', { class: 'prose' }, isIL() ? ilNote : verdict[2]),
        h('div', { class: 'tests' }, ir.tests.map(function (t) {
          return h('div', { class: 'test' }, t.on === null ? chip('No data', '') : t.on ? chip('Yes', 'neg') : chip('No', 'pos'),
            h('span', null, h('b', null, str(t.label, 80)), h('span', { class: 'part-text' }, ' ' + str(t.text, 160))));
        }))));
    }

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

    var groups = [['Stocks', ['SPY', 'QQQ', 'IWM', 'RSP', 'VXUS', 'VEA', 'VWO', '^TA125.TA']], ['Bonds and cash', ['BND', 'SHY', 'IEF', 'TLT', 'TIP', 'LQD', 'HYG', 'SGOV']],
      ['Real assets', ['IAU', 'CL=F', 'DBC', 'VNQ']], ['Crypto', ['BTC-USD', 'ETH-USD', 'SOL-USD']], ['Currencies', ['DX-Y.NYB', 'EURUSD=X', 'JPY=X', 'ILS=X']]];
    var tb = h('tbody');
    groups.forEach(function (g) {
      var rows = g[1].filter(function (k) { return s.assets[k]; });
      if (!rows.length) return;
      tb.appendChild(h('tr', { class: 'group' }, h('th', { colspan: '8', scope: 'colgroup' }, g[0])));
      rows.forEach(function (k) {
        var a = s.assets[k];
        var td = function (x) { return h('td', { class: 'num ' + dirClass(x) }, pct(x)); };
        tb.appendChild(h('tr', null, h('th', { scope: 'row' }, str(a.name, 40), h('span', { class: 'sym' }, k.replace('=X', '').replace('=F', '').replace('-USD', '').replace('.NYB', '').replace('^', '').replace('.TA', ''))),
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
      h('p', { class: 'note' }, 'Shown for context and not scored. Past cycles peaked 12 to 18 months after a halving and then fell hard, but that is four overlapping examples, each weaker than the last. The 200-week average has marked the low area of earlier bear markets.')));
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
      h('li', null, 'Size is the protection. The plan never exceeds your ceiling, never puts more than a tenth of your stock money in crypto, and leaves it out for money needed within four years.'),
      h('li', null, 'Expect an 80% fall and a wait of two to four years at some point. It has happened four times.'),
      h('li', null, 'Bitcoin now falls with the stock market in bad times. It is not insurance.'),
      h('li', null, 'Where you hold it can fail even if Bitcoin does not. A spot fund avoids that. On an exchange, keep only what you could lose.'),
      h('li', null, 'Selling coins is taxable in the US. To cut back, point new money elsewhere first.'),
      h('li', null, 'Trim back to target if the slice grows past one and a half times its size. Left alone, a winning crypto slice can come to steer the whole portfolio.'))));
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
      root.appendChild(callout('info', 'Does any of this change your plan? Usually not', 'The plan has already weighed these stories. News can make it more careful by a small amount and can never make it bolder, because investors who trade on headlines have earned less than those who do nothing. Read this to understand what is happening, not to decide what to do today.'));

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
              chips.length ? h('div', { class: 'row' }, h('span', { class: 'note' }, 'Leans on'), chips) : h('div', { class: 'row' }, h('span', { class: 'note' }, 'No clear push on any part of the plan')),
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
  var ASK_SUGGEST = ['Explain my plan like I’m new to investing', 'Why is the plan holding less gold and fewer bonds right now?', 'What is the single biggest risk to my plan this month?', 'Why does crypto carry more risk than its share of my money?', 'What would have to change for the plan to change?'];
  function askContext() {
    var pl = currentPlan(), s = S.snap, b = S.brief, L = [];
    L.push('PROFILE: investing ' + money(pl.profile.amount) + ', needs the money in ' + years(pl.profile.horizon) + ', risk answer ' + pl.profile.risk + '/5 (' + pl.riskName + '), crypto ceiling ' + E.CRYPTO_CAP[pl.profile.crypto] + '%, signal strength "' + pl.profile.style + '", emergency fund: ' + (pl.profile.efund ? 'yes' : 'no') + ', high-interest debt: ' + (pl.profile.debt ? 'yes' : 'no') + '.');
    var sit = pl.profile.situation, ft = pl.first;
    L.push('COUNTRY: ' + C().name + '. All of the person\u2019s amounts are in ' + (isIL() ? 'Israeli shekels' : 'their own currency, shown with $') + '.');
    L.push('SITUATION: work status ' + sit.status + '; monthly income before tax ' + (sit.income ? money(sit.income) : 'not given') + '; monthly spending ' + (sit.spending ? money(sit.spending) : 'not given') + '; quick savings ' + money(sit.savings) + '; costliest debt ' + (sit.debt ? money(sit.debt) + ' at ' + sit.debtRate + '%' : 'none entered') + (isIL() ? '; employer study fund (Keren Hishtalmut): ' + sit.studyFund + '; pension being paid: ' + sit.pension : '') + '.');
    if (ft.known) L.push('ORDER FOR THIS DEPOSIT: ' + money(Math.round(ft.toDebt)) + ' to debt, ' + money(Math.round(ft.toSavings)) + ' to the cushion (aim ' + ft.months + ' months of spending), ' + money(Math.round(ft.invest)) + ' invested.');
    if (isIL()) {
      var ilf = ilFacts(), cc = C();
      L.push('ISRAEL (tax year ' + cc.taxYear + ', from published summaries, not verified against the Tax Authority): Bank of Israel rate ' + ilf.rate + '%; inflation ' + ilf.cpi + '% (' + ilf.cpiAsOf + '); capital gains tax 25% of the gain after inflation, on sale; Keren Hishtalmut exempt salary ceiling ' + money(cc.studyCeil) + ' a month, tax-free after 6 years, self-employed cap ' + money(cc.studySelfCap) + ' a year; Kupat Gemel LeHashkaa cap ' + money(cc.gemelCap) + ' a year; US-listed funds are a poor fit for Israelis (dividend withholding, US estate tax above $60,000), so use Israeli tracking funds or Irish-domiciled funds; the bond and cash parts are held in shekels and US bond readings are not applied to them.' + (sit.income ? ' Top income-tax rate at this income: ' + ilIncomeTax(sit.income).top + '%.' : ''));
      L.push('NEXT STEPS SHOWN TO THE PERSON: ' + nextSteps(pl).map(function (st, i) { return (i + 1) + '. ' + st[0]; }).join(' '));
    }
    L.push('PLAN (baseline% -> target%, amount of this deposit): ' + pl.rows.map(function (r) { return r.label + ' ' + r.base + '->' + r.target + '% ' + money(Math.round(r.amount)); }).join('; ') + '.');
    L.push('Share of risk by part: ' + pl.rows.filter(function (r) { return r.target > 0; }).map(function (r) { return r.label + ' ' + Math.round(r.riskShare * 100) + '%'; }).join(', ') + '. Expected yearly swing ' + pct(pl.risk.vol, 0, false) + '.');
    L.push('Scenarios for this mix: ' + pl.stress.scenarios.map(function (sc) { return sc.id + ' ' + pct(sc.pct / 100, 0); }).join(', ') + '. Suggested pacing: ' + (pl.pacing.mode === 'now' ? 'all at once' : pl.pacing.steps + ' monthly steps') + '.');
    L.push('Growth range in today\u2019s money over ' + years(pl.profile.horizon) + ': ' + money(Math.round(pl.outlook.value.low)) + ' to ' + money(Math.round(pl.outlook.value.high)) + ', middle ' + money(Math.round(pl.outlook.value.mid)) + ' (' + pl.outlook.mid.toFixed(1) + '% a year after inflation), paying in ' + money(Math.round(pl.outlook.paidIn)) + '.');
    L.push('RULES OF THE MODEL: leans are small (a full negative reading trims a part by ' + Math.round(pl.lean.down * 100) + '%, a full positive adds ' + Math.round(pl.lean.up * 100) + '%); news can only make the plan more careful; act only when a part is 5 points or a quarter of its size off target; check monthly at most.');
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
  var ASK_RULES = 'You are the assistant inside Market Compass, a personal investing dashboard. Answer the question using the data below plus general, well-established investing knowledge. You cannot browse; if something is not in the data, say so. Write for a beginner: plain words, short paragraphs, no more than about 180 words unless asked for more, and define any jargon you use. Be direct about what the data says and honest about uncertainty. Never promise returns or tell the person a price will go up or down. If asked whether now is a good or bad time to buy or sell something, say plainly that nobody can know, and point back to the plan and its check-in rule. If the person wants to change their plan because of news or a recent price move, suggest waiting 48 hours first, and remind them that investors who trade on headlines have earned less than those who do nothing. If asked to pick individual stocks or small coins, explain briefly why the plan uses broad funds instead. Use the person\u2019s country, currency and situation from the data; do not give US-specific advice to someone in another country. For tax or legal questions, give the general rule from the data, say it should be checked with the tax authority or a licensed adviser, and never invent a threshold or rate that is not in the data. Do not use markdown headings or tables.\n\n';
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

  // -------------------------------------------------------------------- learn
  /* What the books and the research behind them teach. s = strength of evidence:
     3 strong, 2 mixed, 1 weak. Each lesson says how this app applies it. */
  var LIBRARY = [
    { theme: 'Before you invest', intro: 'The steps that beat any choice of investment.', items: [
      { t: 'Pay yourself first, and make it automatic.', d: 'When saving was made the default at one US employer, the share of staff taking part rose from 37% to 86%. Willpower is not a plan.', src: 'Clason, The Richest Man in Babylon; Sethi, I Will Teach You to Be Rich; Madrian and Shea (2001)', s: 3, use: 'The monthly deposit field, and the nudge to automate it.' },
      { t: 'Early on, how much you add matters more than what it earns.', d: 'After 10 years at 7% a year, 70% of the balance is your own deposits. After 40 years it is 19%.', src: 'Bernstein, If You Can; arithmetic', s: 3, use: 'The growth chart separates what you paid in from what it earned.' },
      { t: 'Start now rather than later.', d: '$200 a month from age 22 to 65 at 7% grows to about $614,000. Starting at 32 gives about $294,000.', src: 'Malkiel, A Random Walk Down Wall Street; arithmetic', s: 3, use: 'Change the horizon slider and watch the growth range.' },
      { t: 'Follow the order of operations.', d: 'Take any employer match first (a 50% match is an instant 50% return), clear high-interest debt, build 3 to 6 months of cash, then use tax-advantaged accounts before ordinary ones.', src: 'Lindauer, Larimore and LeBoeuf, The Bogleheads’ Guide to Investing; Collins, The Simple Path to Wealth', s: 3, use: 'The warnings at the top of your plan.' }
    ] },
    { theme: 'What to own', intro: 'The mix matters more than anything you pick inside it.', items: [
      { t: 'Your mix of stocks, bonds and cash drives most of the result.', d: 'It explains about 90% of how a fund’s returns vary over time, and the average fund’s timing and stock-picking added nothing on top.', src: 'Brinson, Hood and Beebower (1986); Ibbotson and Kaplan (2000)', s: 3, use: 'Your timeline and nerve set the baseline before any signal is read.' },
      { t: 'Own the whole market instead of choosing stocks.', d: 'About 4% of US stocks produced all of the market’s gain over Treasury bills between 1926 and 2016. Most individual stocks did worse than bills.', src: 'Bessembinder, Do Stocks Outperform Treasury Bills? (2018)', s: 3, use: 'Every part of the plan is a broad index fund.' },
      { t: 'Cheap index funds beat most professionals.', d: '89% of actively managed US large-company funds trailed the S&P 500 over the five years to 2025. The cheapest fifth of funds succeeded 62% of the time; the dearest fifth, 20%.', src: 'S&P SPIVA scorecard (2025); Morningstar (2016); Bogle, The Little Book of Common Sense Investing', s: 3, use: 'The example funds cost about 0.05% a year.' },
      { t: 'Fees compound against you.', d: 'A 1% yearly fee takes about 31% of a lump sum over 40 years.', src: 'Bogle, Common Sense on Mutual Funds; SEC investor bulletin on fees', s: 3, use: 'The fee line under your growth range.' },
      { t: 'Own the world, not one country.', d: 'US stocks earned 6.6% a year after inflation since 1900; the rest of the world earned 4.3%. Japan was the world’s largest market in 1989 and took 34 years to regain that peak.', src: 'Dimson, Marsh and Staunton, Global Investment Returns Yearbook (2026)', s: 3, use: 'About a third of your stocks are international, close to the world’s actual weights.' },
      { t: 'Time does not make stocks safe.', d: 'Across developed markets there has been roughly a 12% chance of losing money after inflation over 30 years. On US data alone it looks like 1%.', src: 'Anarkulova, Cederburg and O’Doherty (2022); Pastor and Stambaugh (2012)', s: 2, use: 'Stocks and crypto never exceed 90% of the plan, however long the horizon.' },
      { t: 'Expect less than the past.', d: 'Return is the starting yield, plus growth, plus any change in what investors will pay. From today’s prices a balanced portfolio is expected to earn roughly 3.4% a year after inflation, against nearly 5% historically.', src: 'Bogle, The Little Book of Common Sense Investing; AQR capital market assumptions (2026)', s: 2, use: 'The growth range is built from today’s yields, not from past returns.' },
      { t: 'A bond’s yield today is roughly what it will earn.', d: 'Starting yield and the following 10-year return on the US bond index have a correlation of about 0.9.', src: 'Leibowitz, Bova and Kogelman (2014); Ilmanen, Expected Returns', s: 3, use: 'The plan’s bond forecast is simply today’s yield less inflation.' },
      { t: 'Gold is insurance against disorder, with a small return.', d: 'About 1.3% a year after inflation since 1900. It fell in 13 of the 28 years when inflation was above 3%, and rose in 8 of 11 major stock-market falls since 1975.', src: 'Erb and Harvey, The Golden Dilemma (2013); Dimson, Marsh and Staunton (2026)', s: 2, use: 'Gold is 5% at most, and described as insurance, not as an inflation hedge.' },
      { t: 'Simple rules beat clever optimisers.', d: 'None of 14 portfolio-optimising models reliably beat simply holding equal amounts.', src: 'DeMiguel, Garlappi and Uppal (2009)', s: 3, use: 'Fixed, readable rules. No optimiser.' }
    ] },
    { theme: 'Timing and signals', intro: 'Why this app leans gently, and why "not at all" is a respectable choice.', items: [
      { t: 'Trend rules are a seatbelt, not an engine.', d: 'Holding an asset only above its long-run average has cut the depth of losses more than it has raised returns, and it lagged for years after 2009.', src: 'Faber (2007); Hurst, Ooi and Pedersen, A Century of Evidence on Trend-Following (2017)', s: 2, use: 'Trend can trim a part further than it can add to it.' },
      { t: 'Any strategy looks better in a backtest than in life.', d: 'Across 97 published market patterns, returns were 58% lower after publication.', src: 'McLean and Pontiff (2016)', s: 3, use: 'A full reading moves a part by a third at most on the default setting.' },
      { t: 'Most indicators have not predicted the market in real time.', d: 'In a review of the best-known predictors, none would have helped an investor beat a simple historical average.', src: 'Welch and Goyal (2008); Goyal, Welch and Zafirov (2024)', s: 3, use: 'The yield curve, the VIX and the earnings-yield comparison are shown but no longer scored.' },
      { t: 'Valuation is a ten-year guide, not a timing tool.', d: 'The Shiller P/E explains about a third of the variation in the next ten years of returns and almost none of the next year.', src: 'Shiller, Irrational Exuberance; Asness, Ilmanen and Maloney, Market Timing: Sin a Little (2017)', s: 3, use: 'Valuation is a tenth of the stock reading and caps how far the plan may lean in.' },
      { t: 'Real tactical funds lost to doing nothing.', d: 'Over ten years, 30 of 34 tactical funds trailed a version of their own holdings that never traded.', src: 'Morningstar (2023)', s: 3, use: 'The "not at all" setting, and small leans otherwise.' },
      { t: 'A recession warning is not a sell signal.', d: 'Switching from stocks to bills when the yield curve inverted lost money in all 24 tests from 1975 to 2018. The curve was inverted from 2022 to 2024 with no recession.', src: 'Fama and French, Inverted Yield Curves and Expected Stock Returns (2019)', s: 3, use: 'The yield curve is displayed as a gauge only.' }
    ] },
    { theme: 'Inflation and interest rates', intro: 'What changes when prices, not growth, are the worry.', items: [
      { t: 'Inflation shocks hurt stocks and bonds together.', d: 'In US inflation surges since 1926, a classic stock-and-bond mix lost about 6% a year after inflation and long Treasuries about 8%.', src: 'Neville, Draaisma, Funnell, Harvey and Van Hemert, The Best Strategies for Inflationary Times (2021)', s: 3, use: 'Four inflation tests decide how the bond part should be held.' },
      { t: 'Bonds are safe from default, not from inflation.', d: 'In 2022 the broad US bond index lost 13%, its worst year since 1976, while stocks fell too.', src: 'Dimson, Marsh and Staunton (2026); AQR, A Changing Stock-Bond Correlation (2023)', s: 3, use: 'The 2022 row in the stress test.' },
      { t: 'Great earnings cannot rescue an overpriced market.', d: 'Investors have paid about 23 times earnings when inflation was under 3% and about 15 times when it was above.', src: 'Shiller, Irrational Exuberance; J.P. Morgan data', s: 2, use: 'Strong profits in the news do not lift the stock reading.' },
      { t: 'Rate rises lower returns but are not a reason to sell.', d: 'The S&P 500 rose in 11 of 12 periods of Fed rate increases, with an average fall of about 14% along the way in the first year.', src: 'Bernanke and Kuttner (2005); Truist and Ned Davis data', s: 2, use: 'A jump in yields trims the stock reading slightly and nothing more.' },
      { t: 'Oil spikes act like a tax.', d: 'Ten of eleven US recessions after 1945 followed a spike in oil prices.', src: 'Hamilton, Historical Oil Shocks (2011)', s: 2, use: 'Oil against its recent high is shown beside the risk dial.' },
      { t: 'Gold stopped following interest rates.', d: 'Its link to inflation-adjusted yields was 84% from 2005 to 2021 and close to zero since 2022, as central banks bought over 1,000 tonnes a year.', src: 'World Gold Council and RBC data', s: 2, use: 'Interest rates are now a tenth of the gold reading, down from a fifth.' }
    ] },
    { theme: 'Your own behaviour', intro: 'The part of investing you control.', items: [
      { t: 'The more people trade, the less they earn.', d: 'Among 66,000 households, the most active earned 11.4% a year while the market made 17.9%.', src: 'Barber and Odean, Trading Is Hazardous to Your Wealth (2000)', s: 3, use: 'The check-once-a-month rule, and no alerts.' },
      { t: 'Bad timing costs about a point a year.', d: 'Investors earned 8.7% a year in funds that returned 9.9%. The gap was smallest in all-in-one funds and largest in the most volatile ones.', src: 'Morningstar, Mind the Gap (2025)', s: 3, use: 'The simpler three-fund and one-fund versions of your plan.' },
      { t: 'Losses hurt about twice as much as gains please, so look less often.', d: 'A review of 607 measurements puts the ratio near 2. The more often people see results, the less risk they can bear.', src: 'Kahneman, Thinking, Fast and Slow; Benartzi and Thaler (1995); Brown and others (2024)', s: 2, use: 'The risk question is asked in dollars over three years, not as a percentage.' },
      { t: 'Selling in a crash usually locks in the loss.', d: 'Savers who left stocks in 2008 and stayed out saw balances rise about 2% by 2011, against about 50% for those who held. Nearly a third of panic sellers never came back.', src: 'Fidelity (2011); Elkind and others, When Do Investors Freak Out? (2022)', s: 3, use: 'The one-page plan says in advance what you will do: nothing.' },
      { t: 'The worst so far is not the worst possible.', d: 'Every record loss was larger than the record before it.', src: 'Taleb, The Black Swan; Taleb, Fooled by Randomness', s: 2, use: 'The stress test says plainly that it is not a floor.' },
      { t: 'Apps that prompt action make people trade more.', d: 'In a controlled experiment, rewarding trades with points produced 39% more of them.', src: 'Ontario Securities Commission (2022); Barber and others on Robinhood (2022)', s: 2, use: 'No notifications, no top movers, no daily profit and loss.' },
      { t: 'A lump sum usually beats drip-feeding it.', d: 'Investing at once beat spreading over months 68% of the time from 1976 to 2022.', src: 'Vanguard, Cost Averaging: Invest Now or Temporarily Hold Your Cash? (2023)', s: 3, use: 'Stepping in is offered only if you gave a nervous answer.' },
      { t: 'Write your rules while you are calm.', d: 'There is no controlled proof that a written plan helps, but it costs nothing and the people who study investor behaviour recommend it.', src: 'Zweig, Your Money and Your Brain; Ellis, Winning the Loser’s Game', s: 1, use: 'Your plan on one page.' },
      { t: 'The market’s mood is an offer, not an instruction.', d: 'Prices swing far more than the value of the businesses behind them. You are free to ignore the quote.', src: 'Graham, The Intelligent Investor; Marks, The Most Important Thing', s: 2, use: 'News can make this plan more careful, and never bolder.' }
    ] },
    { theme: 'Crypto', intro: 'Neither a miracle nor a fraud. A very volatile asset that needs sizing.', items: [
      { t: 'Size is your main protection.', d: 'In a standard portfolio a 2% Bitcoin holding carries about 5% of the total risk, and 4% carries about 14%.', src: 'BlackRock, Sizing Bitcoin in Portfolios (2024)', s: 2, use: 'Crypto is at most a tenth of your stock money, and its share of risk is shown.' },
      { t: 'Expect an 80% fall and a wait of two to four years.', d: 'Bitcoin has fallen 93%, 84%, 83% and 78% in its four completed busts.', src: 'Harvey and others, An Investor’s Guide to Crypto (2022)', s: 3, use: 'None for money needed within four years; 85% in the stress test.' },
      { t: 'It falls with stocks in bad times.', d: 'Its link to US shares went from zero before 2020 to about 0.5 in the five years to 2026.', src: 'IMF (2022); AQR (2026)', s: 3, use: 'Risk conditions are a quarter of the crypto reading.' },
      { t: 'Crypto trends are real but short.', d: 'Momentum shows up over days to weeks and tends to reverse beyond a month.', src: 'Liu and Tsyvinski (2021); Liu, Tsyvinski and Wu (2022)', s: 2, use: 'The crypto trend reading leans on 50- and 100-day averages, not a year.' },
      { t: 'Popular indicators mostly follow price.', d: 'Fund flows match the same day’s price move but say almost nothing about the next week. Stablecoin issuance has no reliable lead in the published tests.', src: 'Lyons and Viswanath-Natraj; DWF Labs flow study', s: 1, use: 'Flows are reported in the news brief; stablecoins and mood are a twentieth each.' },
      { t: 'Most people buy after prices have soared.', d: 'About three in four users of crypto apps probably lost money on Bitcoin between 2015 and 2022.', src: 'Bank for International Settlements, Bulletin 69 (2023)', s: 2, use: 'Crypto buys are split into at least three.' },
      { t: 'The place you hold coins can fail even if Bitcoin does not.', d: 'Mt. Gox lost 650,000 or more coins in 2014. About $3.4 billion was stolen from platforms in 2025, and $6.3 billion from one exchange in October 2026.', src: 'Chainalysis; court records; Faux, Number Go Up', s: 3, use: 'The plan suggests a spot fund, or a regulated platform with limits.' },
      { t: 'Most small coins die.', d: 'More than half of the tokens tracked since 2021 had stopped trading by the end of 2025.', src: 'CoinGecko (2026); Liu, Tsyvinski and Wu (2022)', s: 3, use: 'The plan holds Bitcoin and a little Ether, nothing smaller.' },
      { t: 'Four cycles prove little.', d: 'The "four-year cycle" rests on four overlapping examples, and each has been weaker than the last.', src: 'Grayscale research; Liu and Tsyvinski (2021)', s: 1, use: 'The halving clock is shown for context and scores nothing.' }
    ] },
    { theme: 'Accounts, tax and scams (US)', intro: 'Rules change every year. Check the official source before acting.', items: [
      { t: 'Use a tax-sheltered account before an ordinary one.', d: 'For 2026 the limit is $7,500 for an IRA and $24,500 for a 401(k). A Roth IRA needs earned income and suits people in a low tax bracket today; what you paid in can come out again without tax.', src: 'IRS; Collins, The Simple Path to Wealth', s: 3, use: 'Not built in. Choose the account first, then apply this mix inside it.' },
      { t: 'Hold for more than a year where you can.', d: 'Gains on assets held over a year are taxed at lower rates than those sold sooner. Every sale of crypto is taxable; it is treated as property.', src: 'IRS; The Bogleheads’ Guide to Investing', s: 3, use: 'Rebalance with new money first, and sell last.' },
      { t: 'Rebalance rarely, by rule.', d: 'No schedule beats another. Checking once or twice a year and acting at a 5-point gap needed about 28 trades in 84 years.', src: 'Vanguard, Best Practices for Portfolio Rebalancing (2015); Bernstein, The Intelligent Asset Allocator', s: 3, use: 'The 5-point band in your plan.' },
      { t: 'High returns with little risk is the classic sign of fraud.', d: 'So are pressure to act now, "everyone is buying it", and sellers who are not licensed. $1.1 billion was lost to investment scams on social media in 2025.', src: 'SEC, investor.gov; FINRA Foundation; FTC', s: 3, use: 'This app names only large, regulated index funds.' },
      { t: 'Know what "enough" is.', d: 'A sum of about 25 times your yearly spending has historically supported that spending for 30 years.', src: 'Bengen (1994); Robin and Dominguez, Your Money or Your Life', s: 2, use: 'Set the horizon to when you want to reach it.' }
    ] }
  ];
  var LIBRARY_IL = { theme: 'Investing from Israel', intro: 'Rules for tax year 2026, from published summaries. Check a figure with the Tax Authority or a licensed adviser before acting on it.', items: [
    { t: 'Take the Keren Hishtalmut before anything else.', d: 'Where an employer offers it, they typically add 7.5% of your salary to your own 2.5%, free of tax on salary up to \u20AA15,712 a month, and gains come out tax-free after six years.', src: 'Israeli tax guides for 2026; The Jerusalem Post year-end tax guide', s: 3, use: 'It leads your next steps when you say you are an employee.' },
    { t: 'Tax is 25% of the gain after inflation, and only when you sell.', d: 'Nothing is due while you hold. Dividends are taxed at 25% as well. A further surtax applies only above about \u20AA721,560 of yearly income.', src: 'PwC tax summary for Israel (2026)', s: 3, use: 'The plan rebalances with new money, so that selling is the last resort.' },
    { t: 'Avoid US-listed funds.', d: 'An Irish-domiciled fund pays 15% US tax on dividends inside the fund. A US-listed fund held from Israel has a quarter or more withheld, and US assets above $60,000 can face US estate tax of up to 40%. Israel itself has no inheritance tax, which is why this catches people out.', src: 'Globes, The US estate tax trap for Israeli investors', s: 3, use: 'The examples are Israeli tracking funds or Irish-domiciled funds, never VOO or VTI.' },
    { t: 'Tracking mutual funds usually cost nothing to buy or sell.', d: 'Israeli mutual funds, index trackers included, do not charge a separate trading commission, unlike exchange-traded funds. You still pay the yearly management fee, and a bank may charge for custody.', src: 'Meitav; Globes', s: 2, use: 'They are the first suggestion for small monthly amounts.' },
    { t: 'Keep the steady part of your money in shekels.', d: 'The dollar has ranged from about \u20AA2.80 to \u20AA3.82 in two years. Your rent and bills are in shekels, so the part of the plan meant to be stable should be too.', src: 'Bank of Israel; exchange-rate data', s: 3, use: 'Bonds and cash are shekel instruments, and US bond readings are not applied to them.' },
    { t: 'Your country is already a large bet.', d: 'Your salary, home and pension all depend on Israel\u2019s economy. A strong run at home (the Tel Aviv 125 rose about 70% in two years) tempts people to add more just when it is dearest.', src: 'Dimson, Marsh and Staunton on single-country risk', s: 2, use: 'Israeli shares are a modest part of the international slice, not the core.' },
    { t: 'A Kupat Gemel LeHashkaa trades a higher fee for flexibility.', d: 'It takes up to \u20AA83,641 a year, lets you switch investment tracks without tax, and is taxed at 25% of the gain after inflation when you withdraw.', src: 'Globes, Changes that will affect personal finances in 2026', s: 2, use: 'Offered beside a trading account as one of two sensible homes for the plan.' },
    { t: 'Crypto is taxed like any other asset.', d: 'Gains are taxed at 25%. Frequent trading can be treated as a business and taxed at up to 50%. Keep every record; banks may ask where the money came from.', src: 'Israeli court rulings and Tax Authority guidance, as reported', s: 2, use: 'The plan suggests a Bitcoin tracking fund inside your ordinary account.' },
    { t: 'Rebalance rarely, by rule.', d: 'No schedule beats another. Checking once or twice a year and acting at a 5-point gap needed about 28 trades in 84 years.', src: 'Vanguard, Best Practices for Portfolio Rebalancing (2015); Bernstein, The Intelligent Asset Allocator', s: 3, use: 'The 5-point band in your plan.' },
    { t: 'High returns with little risk is the classic sign of fraud.', d: 'So are pressure to act now, "everyone is buying it", and sellers who are not licensed. Check that anyone offering investments is licensed by the Israel Securities Authority.', src: 'SEC, investor.gov; Israel Securities Authority', s: 3, use: 'This app names only broad index funds from large managers.' },
    { t: 'Know what "enough" is.', d: 'A sum of about 25 times your yearly spending has historically supported that spending for 30 years.', src: 'Bengen (1994); Robin and Dominguez, Your Money or Your Life', s: 2, use: 'Set the horizon to when you want to reach it.' }
  ] };
  function libraryThemes() { return isIL() ? LIBRARY.slice(0, -1).concat([LIBRARY_IL]) : LIBRARY; }
  var READING = [
    ['If You Can', 'William Bernstein', 'Sixteen free pages. The whole plan in one sitting.'],
    ['The Little Book of Common Sense Investing', 'John Bogle', 'Why owning everything cheaply beats trying to choose.'],
    ['The Simple Path to Wealth', 'JL Collins', 'One fund, held through every crash.'],
    ['The Psychology of Money', 'Morgan Housel', 'Why behaviour matters more than knowledge.'],
    ['A Random Walk Down Wall Street', 'Burton Malkiel', 'The evidence, and a guide for each stage of life.'],
    ['The Intelligent Investor', 'Benjamin Graham, with Jason Zweig’s commentary', 'Mr. Market and the margin of safety.'],
    ['The Four Pillars of Investing', 'William Bernstein', 'Theory, history, psychology and the business of investing.'],
    ['The Most Important Thing', 'Howard Marks', 'How to think about risk and cycles.']
  ];
  var STRENGTH = { 3: ['Strong evidence', 'pos'], 2: ['Mixed evidence', ''], 1: ['Weak evidence', 'warn'] };

  function renderLearn() {
    var root = clear($('view-learn'));
    var themes = libraryThemes();
    var count = themes.reduce(function (a, g) { return a + g.items.length; }, 0);
    root.appendChild(h('section', { class: 'card stack' },
      h('span', { class: 'eyebrow' }, count + ' lessons from the books and the research behind them'),
      h('p', { class: 'lede' }, 'What a century of investing writing agrees on, where it disagrees, and how this app uses each lesson.'),
      h('p', { class: 'note' }, 'Gathered in November 2026 across the major investing books and the studies they rest on. Figures come from published summaries and abstracts, not from the full texts, and a few are from memory. Treat them as a careful reader’s notes and check a number at its source before relying on it.')));
    themes.forEach(function (g) {
      var box = h('section', { class: 'card stack' }, h('h2', null, g.theme), h('p', { class: 'sub' }, g.intro));
      var listEl = h('div', { class: 'lessons' });
      g.items.forEach(function (it) {
        var st = STRENGTH[it.s];
        listEl.appendChild(h('article', { class: 'lesson' },
          h('div', { class: 'row' }, h('h3', { class: 'grow' }, it.t), chip(st[0], st[1])),
          h('p', null, it.d),
          h('p', { class: 'note' }, it.src),
          h('p', { class: 'use' }, h('b', null, 'In this app: '), it.use)));
      });
      box.appendChild(listEl);
      root.appendChild(box);
    });
    root.appendChild(h('section', { class: 'card stack' },
      h('h2', null, 'Eight books, in the order to read them'),
      h('ol', { class: 'steps' }, READING.map(function (b) {
        return h('li', null, h('h3', null, b[0]), h('p', null, b[1] + '. ' + b[2]));
      })),
      h('p', { class: 'note' }, 'For crypto, read Saifedean Ammous’s The Bitcoin Standard alongside a critical review, then Zeke Faux’s Number Go Up.')));
  }

  // ------------------------------------------------------------------- method
  function renderMethod() {
    var root = clear($('view-method'));
    root.appendChild(card('How the plan is built', 'Four steps, in order of how much they matter.',
      h('ol', { class: 'steps' },
        h('li', null, h('h3', null, 'First, the things that beat any investment'), h('p', null, 'Paying off high-interest debt and holding an emergency cushion come before everything else. If either is missing, the plan says so at the top.')),
        h('li', null, h('h3', null, 'Your timeline and nerve set a baseline mix'), h('p', null, 'How soon you need the money caps the share in stocks and crypto: none within a year, 10% at one to two years, 20% at two to three, 35% at three to five, 50% at five to seven, 70% at seven to ten, 85% at ten to fifteen, and 90% beyond. The test behind each step is that if stocks halved, the loss would be one your goal could survive in the time left. Your answer to the falling-prices question then picks a level from 20% to 90%. Stocks are split 65% US and 35% international, with up to 5% gold. The rest is bonds and cash.')),
        h('li', null, h('h3', null, 'Live readings lean each part, gently'), h('p', null, 'Each part gets a reading from ' + MINUS + '1 to +1. For stocks it is 70% trend (price against its 200-day average and 12-month return against T-bills), 20% risk conditions (credit markets, recent volatility, a jump in interest rates, breadth) and 10% valuation, measured against its own last 40 years. Bonds weigh trend, yield after inflation, and the level and direction of inflation. Gold is three-quarters trend. Crypto is two-thirds trend on shorter averages. On the default setting a full negative reading trims a part by 35% of its size and a full positive one adds 20%.')),
        h('li', null, h('h3', null, 'Hard limits, and news only as a brake'), h('p', null, 'Whatever is trimmed waits in T-bills. Crypto never exceeds your ceiling or a tenth of your stock money. Growth assets never exceed your timeline cap. The news brief can make a reading more careful by a tenth at most. It can never make the plan bolder, and it cannot turn a positive lean into a negative one.')))));

    root.appendChild(card('What the research changed', 'The first version of this model was rebuilt after six research passes through the investing literature. These are the changes, each made because the evidence pointed against the original choice.',
      h('ul', { class: 'bullets' },
        h('li', null, h('b', null, 'News counts for less. '), 'It was a fifth of every reading and could push in either direction. It is now a tenth at most and can only add caution. Acting on headlines is the least supported idea in the research.'),
        h('li', null, h('b', null, 'Three popular gauges no longer score. '), 'The yield curve, the VIX and the gap between stock earnings yield and bond yields are shown for context only. None has predicted stock returns in real time.'),
        h('li', null, h('b', null, 'Valuation is judged against its own recent past. '), 'A fixed "normal" Shiller P/E of 25 had read "expensive" almost every month since 2014, which amounts to a permanent underweight.'),
        h('li', null, h('b', null, 'Trend uses two slow readings, not four. '), 'The 50-day against 200-day comparison repeated what the others already said. Crypto now uses shorter averages, where its evidence is.'),
        h('li', null, h('b', null, 'Leans are smaller and lopsided. '), 'Trend rules have cut losses more than they have raised returns, so the plan trims further than it adds. The strongest setting came down from 70% to 50%.'),
        h('li', null, h('b', null, 'The ceiling on stocks is 90%, not 100%, '), 'and the steps for money needed within ten years are lower. Long horizons do not make stocks safe.'),
        h('li', null, h('b', null, 'Crypto is sized by risk. '), 'At most a tenth of your stock money, none for the most cautious answer, none for money needed within four years.'),
        h('li', null, h('b', null, 'Pacing ignores the market. '), 'Suggesting slower buying when markets look stressed was a form of market timing. Stepping in is now offered only for nerves.'),
        h('li', null, h('b', null, 'The stress test uses real episodes. '), '2008, when bonds helped, and 2022, when they did not, alongside the harsh all-at-once case.'),
        h('li', null, h('b', null, 'Bonds change shape with inflation. '), 'When inflation is driving markets the plan says to hold shorter and inflation-linked bonds.'),
        h('li', null, h('b', null, 'Added: '), 'your share of risk by part, a growth range built from today’s yields, a three-fund version, a one-page written plan, and a check-once-a-month rule.'))));

    if (isIL()) root.appendChild(card('What is different for Israel', 'The market readings are global. What you do with them is local.',
      h('ul', { class: 'bullets' },
        h('li', null, h('b', null, 'Amounts are in shekels. '), 'Prices of funds and coins on the Markets and Crypto tabs stay in dollars, because that is how they are quoted.'),
        h('li', null, h('b', null, 'The steady part is in shekels. '), 'Bonds and cash mean Israeli government bonds, Makam and money-market funds. The readings for US bonds and the US inflation tests are not applied to them, so that part stays at its baseline.'),
        h('li', null, h('b', null, 'Growth estimates use Israeli rates. '), 'Cash is expected to earn the Bank of Israel rate, bonds a little more, both measured against 2% inflation.'),
        h('li', null, h('b', null, 'Your details change the order, not the mix. '), 'Debt costing 7% a year or more is paid first, then a cushion of three months of spending (six if your income is irregular), and only the rest is invested.'),
        h('li', null, h('b', null, 'Currency is a risk the model does not hedge. '), 'Stocks, gold and crypto are priced in dollars. The plan shows the exchange rate and leaves it alone.'),
        h('li', null, h('b', null, 'The tax figures are for 2026 '), 'and come from published summaries, not the Tax Authority. They will change.'))));

    root.appendChild(card('What it cannot do', null, h('ul', { class: 'bullets' },
      h('li', null, 'Predict. Every reading describes what has already happened. Markets regularly do the opposite of what the signals suggest.'),
      h('li', null, 'Beat doing nothing with any confidence. The leans are small because the evidence for them is modest. "Not at all" is a sound setting.'),
      h('li', null, 'Know your whole situation. It cannot see your taxes, income, pension, debts or what you already own unless you enter it. An adviser who can is worth more than any dashboard.'),
      h('li', null, 'Guarantee fresh or perfect data. Prices are delayed, a feed can fail, and the news brief is written by an AI that can misjudge a story. Each source below shows whether it loaded.'),
      h('li', null, 'Replace patience. Over decades, how much you save and how long you stay invested matter far more than any lean on this page.'))));

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
    if (!S.learnBuilt) { renderLearn(); S.learnBuilt = true; }
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
        if (d.exists) { S.profile = E.normalizeProfile(d.data()); S.learnBuilt = false; writeControls(); renderData(); }
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
