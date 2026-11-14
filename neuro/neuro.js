/* neuro: memory mechanisms drawn from small JSON specs. Four views:
   engram     cells compete for a place in a memory; excitability left behind links memories close in time
   attractor  a Hopfield network stores patterns and completes a cue; past capacity it settles on mixtures
   retention  recall probability over time under reviews; a review when recall is harder strengthens more
   rhythm     a cycle split into modes (encode, retrieve), with the inputs that dominate each phase
   Each figure is <figure data-neuro="kind"><script type="application/json">. The models are illustrative
   (stated on the figure), seeded so a page draws the same thing every time.
   No eval, no innerHTML, no inline handlers: a page's CSP needs nothing extra. */
(function () {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg';
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var KEYS = ['pull', 'push', 'irq', 'ok', 'wait', 'crit'];

  function h(tag, cls, parent, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }
  function s(tag, attrs, parent, text) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) if (attrs[k] !== undefined) e.setAttribute(k, attrs[k]);
    if (text !== undefined) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }
  function clear(e) { while (e.firstChild) e.removeChild(e.firstChild); }
  function rng(seed) {                         // mulberry32
    var a = (seed >>> 0) || 1;
    return function () {
      a = (a + 0x6D2B79F5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function col(i, given) { return 'var(--nr-' + (given && KEYS.indexOf(given) >= 0 ? given : KEYS[i % KEYS.length]) + ')'; }
  function pct(x) { return Math.round(x * 100) + ' %'; }
  function paper(fig) { return fig.hasAttribute('data-paper') || (window.matchMedia && matchMedia('print').matches); }
  function head(fig, eyebrow, title, legend) {
    var hd = h('div', 'nr-head', fig);
    var t = h('div', 'nr-title', hd);
    h('span', 'nr-eyebrow', t, eyebrow);
    if (title) h('span', 'nr-name', t, title);
    if (legend && legend.length) {
      var lg = h('div', 'nr-legend', hd);
      legend.forEach(function (l) {
        var li = h('span', 'nr-li', lg);
        var sw = h('span', 'nr-sw', li);
        sw.style.setProperty('--k', l[1]);
        h('span', null, li, l[0]);
      });
    }
    return hd;
  }
  function button(parent, label, title, fn) {
    var b = h('button', 'nr-btn', parent, label);
    b.type = 'button';
    if (title) { b.title = title; b.setAttribute('aria-label', title); }
    b.addEventListener('click', fn);
    return b;
  }
  function slider(parent, label, min, max, step, val, fn) {
    var w = h('label', 'nr-slide', parent);
    h('span', 'nr-dim', w, label);
    var r = h('input', null, w);
    r.type = 'range'; r.min = min; r.max = max; r.step = step; r.value = val;
    var out = h('output', 'nr-out', w);
    r.addEventListener('input', function () { fn(+r.value, out); });
    fn(+r.value, out);
    return r;
  }
  function note(fig, text, cls) { if (text) h('p', 'nr-note' + (cls ? ' ' + cls : ''), fig, text); }

  /* ---- engram: allocation by excitability, linking in time ------------------------------------------ */
  function engramModel(d, events) {
    var n = d.cells || 120, k = d.k || Math.round(n * 0.15), tau = d.tau || 6, boost = d.boost === undefined ? 1 : d.boost;
    // baseline excitability fluctuates: each event meets a fresh draw (seeded per event, so moving one keeps its draw)
    var noise = d.noise === undefined ? 0.6 : d.noise, base = events.map(function (e, j) {
      var r = rng((d.seed || 7) * 131 + j * 977), b = [];
      for (var i = 0; i < n; i++) b.push(r() * noise);
      return b;
    });
    var order = events.map(function (e, i) { return i; }).sort(function (a, b) { return events[a].t - events[b].t; });
    var mem = new Array(events.length);
    function lift(i, t, upto) {
      var e = 0;
      upto.forEach(function (j) {
        if (mem[j] && mem[j].has(i) && t >= events[j].t) e += boost * Math.exp(-(t - events[j].t) / tau);
      });
      return e;
    }
    var done = [];
    order.forEach(function (j) {
      var t = events[j].t, ex = [];
      for (var i = 0; i < n; i++) ex.push(base[j][i] + lift(i, t, done));
      var idx = []; for (i = 0; i < n; i++) idx.push(i);
      idx.sort(function (a, b) { return ex[b] - ex[a] || a - b; });
      mem[j] = new Set(idx.slice(0, k));
      done.push(j);
    });
    return { n: n, k: k, tau: tau, mem: mem, exc: function (i, t) { return noise / 2 + lift(i, t, done); }, chance: k / n };
  }
  function overlap(a, b) { var c = 0; a.forEach(function (x) { if (b.has(x)) c++; }); return c / a.size; }

  function engram(fig, d) {
    var events = d.events.map(function (e) { return { name: e.name, t: +e.t, color: e.color }; });
    var unit = d.unit || 'h';
    var dragI = d.drag ? events.findIndex(function (e) { return e.name === d.drag; }) : -1;
    head(fig, 'ENGRAM', d.title, events.map(function (e, i) { return [e.name, col(i, e.color)]; }));
    var ctl = h('div', 'nr-ctl', fig);
    var body = h('div', 'nr-body nr-engram-body', fig);
    var W = 300, H = 230, svg = s('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'nr-svg nr-field', role: 'img' }, body);
    var side = h('div', 'nr-side', body);
    var tl = s('svg', { viewBox: '0 0 360 120', class: 'nr-svg nr-tl', role: 'img' }, side);
    var tab = h('table', 'nr-tab', side);
    var chanceNote = h('p', 'nr-dim nr-small', side);
    var curve = s('svg', { viewBox: '0 0 360 110', class: 'nr-svg nr-curve', role: 'img' }, side);
    note(fig, d.note);
    note(fig, 'Model: each cell\'s baseline excitability fluctuates (a fresh draw at each event); joining a memory adds a boost that decays with time constant ' +
      (d.tau || 6) + ' ' + unit + '; each event recruits the ' + (d.k || 'top') + ' most excitable cells. Illustrative, not fitted.', 'nr-dim');
    var focus = -1;
    // cell positions: a jittered grid
    var n = d.cells || 120, cols = Math.ceil(Math.sqrt(n * W / H)), rows = Math.ceil(n / cols);
    var pr = rng((d.seed || 7) + 1), pos = [];
    var dx = (W - 20) / cols, dy = (H - 20) / rows;
    for (var i = 0; i < n; i++) {
      var c = i % cols, rr = Math.floor(i / cols);
      pos.push([10 + dx * (c + 0.5) + (pr() - 0.5) * dx * 0.5, 10 + dy * (rr + 0.5) + (pr() - 0.5) * dy * 0.5]);
    }
    var rad = Math.min(dx, dy) * 0.36;
    var tmax = d.horizon || Math.max.apply(null, events.map(function (e) { return e.t; })) * 1.15 + 1;

    function draw() {
      var m = engramModel(d, events);
      clear(svg); clear(tl); clear(tab); clear(curve);
      // field
      for (var i = 0; i < m.n; i++) {
        var who = []; m.mem.forEach(function (S, j) { if (S.has(i)) who.push(j); });
        var g = s('g', { class: 'nr-cell' + (focus >= 0 && who.indexOf(focus) < 0 ? ' nr-fade' : '') }, svg);
        if (!who.length) s('circle', { cx: pos[i][0], cy: pos[i][1], r: rad * 0.55, class: 'nr-idle' }, g);
        else {
          who.forEach(function (j, q) {
            var rr2 = rad * (1 - q * 0.42);
            s('circle', { cx: pos[i][0], cy: pos[i][1], r: Math.max(rr2, rad * 0.3), fill: col(j, events[j].color),
              class: 'nr-on' + (q ? ' nr-inner' : '') }, g);
          });
          if (who.length > 1) s('circle', { cx: pos[i][0], cy: pos[i][1], r: rad + 2.2, class: 'nr-shared' }, g);
        }
        s('title', {}, g, who.length ? 'in ' + who.map(function (j) { return events[j].name; }).join(' and ') : 'in no memory');
      }
      // timeline with the mean excitability of each memory's cells
      var x = function (t) { return 34 + (t / tmax) * 312; };
      s('line', { x1: 34, x2: 346, y1: 96, y2: 96, class: 'nr-axis' }, tl);
      for (var tt = 0; tt <= tmax; tt += niceStep(tmax)) {
        s('line', { x1: x(tt), x2: x(tt), y1: 96, y2: 99, class: 'nr-axis' }, tl);
        s('text', { x: x(tt), y: 110, class: 'nr-tick', 'text-anchor': 'middle' }, tl, tt + ' ' + unit);
      }
      s('text', { x: 4, y: 14, class: 'nr-tick' }, tl, 'excitability');
      events.forEach(function (e, j) {
        var pts = [];
        for (var q = 0; q <= 80; q++) {
          var t = e.t + (tmax - e.t) * q / 80, sum = 0;
          m.mem[j].forEach(function (c) { sum += m.exc(c, t); });
          pts.push(x(t).toFixed(1) + ',' + (90 - Math.min(1, (sum / m.k) / ((d.noise === undefined ? 0.6 : d.noise) + (d.boost || 1))) * 68).toFixed(1));
        }
        s('polyline', { points: pts.join(' '), class: 'nr-trace', stroke: col(j, e.color) }, tl);
        var g = s('g', { class: 'nr-ev' + (j === dragI ? ' nr-drag' : ''), tabindex: 0 }, tl);
        s('line', { x1: x(e.t), x2: x(e.t), y1: 18, y2: 96, stroke: col(j, e.color), class: 'nr-evline' }, g);
        s('circle', { cx: x(e.t), cy: 96, r: 5, fill: col(j, e.color) }, g);
        s('text', { x: x(e.t) + 4, y: 26 + (j % 2) * 11, class: 'nr-evlab' }, g, e.name);
        g.addEventListener('click', function () { focus = focus === j ? -1 : j; draw(); });
        g.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); focus = focus === j ? -1 : j; draw(); } });
      });
      // overlap table
      var tr = h('tr', null, h('thead', null, tab));
      ['pair', 'apart', 'shared cells', ''].forEach(function (t) { h('th', null, tr, t); });
      var tb = h('tbody', null, tab);
      for (var a = 0; a < events.length; a++) for (var b = a + 1; b < events.length; b++) {
        var ov = overlap(m.mem[a], m.mem[b]), linked = ov > m.chance * 2.5;
        var row = h('tr', linked ? 'nr-linked' : null, tb);
        h('td', null, row, events[a].name + ' & ' + events[b].name);
        h('td', null, row, Math.abs(events[b].t - events[a].t).toFixed(1).replace(/\.0$/, '') + ' ' + unit);
        var td = h('td', null, row); var bar = h('span', 'nr-bar', td); bar.style.width = (ov * 100) + '%';
        h('span', 'nr-barlab', td, pct(ov));
        h('td', 'nr-dim', row, linked ? 'linked' : 'separate');
      }
      chanceNote.textContent = 'Chance overlap, for two memories allocated independently: ' + pct(m.chance) + '. Linked: more than 2.5 times chance.';
      // overlap against the interval, for the dragged event and the one before it
      if (dragI > 0) {
        var prev = dragI - 1, gap = events[dragI].t - events[prev].t, span = Math.max(gap * 2.5, (d.tau || 6) * 5);
        var X = function (v) { return 34 + v / span * 312; }, Y = function (v) { return 92 - v * 78; };
        s('line', { x1: 34, x2: 346, y1: 92, y2: 92, class: 'nr-axis' }, curve);
        s('line', { x1: 34, x2: 34, y1: 12, y2: 92, class: 'nr-axis' }, curve);
        s('line', { x1: 34, x2: 346, y1: Y(m.chance), y2: Y(m.chance), class: 'nr-chance' }, curve);
        s('text', { x: 342, y: Y(m.chance) - 3, class: 'nr-tick', 'text-anchor': 'end' }, curve, 'chance');
        s('text', { x: 4, y: 10, class: 'nr-tick' }, curve, 'shared ' + events[prev].name + ' & ' + events[dragI].name);
        s('text', { x: 346, y: 106, class: 'nr-tick', 'text-anchor': 'end' }, curve, 'interval, ' + unit);
        var pts = [], keep = events[dragI].t;
        for (var q = 0; q <= 48; q++) {
          var v = span * q / 48;
          events[dragI].t = events[prev].t + v;
          var mm = engramModel(d, events);
          pts.push(X(v).toFixed(1) + ',' + Y(overlap(mm.mem[prev], mm.mem[dragI])).toFixed(1));
        }
        events[dragI].t = keep;
        s('polyline', { points: pts.join(' '), class: 'nr-trace', stroke: col(dragI, events[dragI].color) }, curve);
        s('circle', { cx: X(Math.min(gap, span)), cy: Y(overlap(m.mem[prev], m.mem[dragI])), r: 4.5, fill: col(dragI, events[dragI].color) }, curve);
      }
    }
    if (dragI >= 0 && !paper(fig)) {
      var t0 = dragI > 0 ? events[dragI - 1].t : 0;
      slider(ctl, 'move ' + events[dragI].name, t0, t0 + (d.slide || tmax - t0), (d.slide || tmax) / 200, events[dragI].t, function (v, out) {
        events[dragI].t = v; out.textContent = (v - t0).toFixed(1) + ' ' + unit + ' after ' + (dragI > 0 ? events[dragI - 1].name : 'start'); draw();
      });
    } else ctl.remove();
    draw();
  }
  function niceStep(span) {
    var raw = span / 6, p = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / p;
    return (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * p;
  }

  /* ---- attractor: a Hopfield network ------------------------------------------------------------------- */
  function attractor(fig, d) {
    var w = d.w, hh = d.h, N = w * hh;
    var pats = d.patterns.map(function (p) {
      var v = []; p.rows.forEach(function (row) { for (var i = 0; i < w; i++) v.push(row[i] === '#' || row[i] === 'X' ? 1 : -1); });
      return { name: p.name, v: v, color: p.color };
    });
    var r = rng(d.seed || 3), extra = 0, Wt = null, state = [], timer = null, sweeps = 0, energy = [];
    var stored = pats.slice();
    function randomPattern(i) { var v = []; for (var q = 0; q < N; q++) v.push(r() < 0.5 ? 1 : -1); return { name: 'r' + i, v: v, rand: true }; }
    function train() {
      Wt = new Float32Array(N * N);
      stored.forEach(function (p) {
        for (var i = 0; i < N; i++) for (var j = 0; j < N; j++) if (i !== j) Wt[i * N + j] += p.v[i] * p.v[j] / N;
      });
    }
    function ovl(p) { var m = 0; for (var i = 0; i < N; i++) m += state[i] * p.v[i]; return m / N; }
    function E() { var e = 0; for (var i = 0; i < N; i++) for (var j = 0; j < N; j++) e -= 0.5 * Wt[i * N + j] * state[i] * state[j]; return e; }
    var cue = d.cue || {}, flip = cue.flip === undefined ? 0.25 : cue.flip;
    function makeCue() {
      var src = pats.find(function (p) { return p.name === cue.pattern; }) || pats[0], cr = rng((d.seed || 3) + 11);
      state = src.v.slice();
      for (var i = 0; i < N; i++) {
        var x = i % w, y = Math.floor(i / w), masked = (cue.mask === 'bottom' && y >= hh / 2) || (cue.mask === 'top' && y < hh / 2) ||
          (cue.mask === 'left' && x < w / 2) || (cue.mask === 'right' && x >= w / 2);
        if (masked) state[i] = -1;
        else if (cr() < flip) state[i] = -state[i];
      }
      sweeps = 0; energy = [E()];
    }
    function sweep() {
      var order = []; for (var i = 0; i < N; i++) order.push(i);
      for (i = N - 1; i > 0; i--) { var j = Math.floor(r() * (i + 1)), t = order[i]; order[i] = order[j]; order[j] = t; }
      var changed = 0;
      order.forEach(function (i) {
        var hsum = 0; for (var j = 0; j < N; j++) hsum += Wt[i * N + j] * state[j];
        var ns = hsum >= 0 ? 1 : -1;
        if (ns !== state[i]) { state[i] = ns; changed++; }
      });
      sweeps++; energy.push(E());
      return changed;
    }
    head(fig, 'ATTRACTOR', d.title, [['stored pattern', 'var(--nr-pull)'], ['cell on', 'var(--nr-ink)']]);
    var ctl = h('div', 'nr-ctl', fig);
    var body = h('div', 'nr-body nr-att-body', fig);
    var gallery = h('div', 'nr-gallery', body);
    var main = h('div', 'nr-att-main', body);
    var grid = s('svg', { viewBox: '0 0 ' + (w * 10) + ' ' + (hh * 10), class: 'nr-svg nr-grid', role: 'img' }, main);
    var status = h('p', 'nr-status', main);
    var spark = s('svg', { viewBox: '0 0 200 40', class: 'nr-svg nr-spark', role: 'img' }, main);
    note(fig, d.note);
    note(fig, 'Hopfield (1982): Hebbian weights from the stored patterns, asynchronous updates, each sweep lowers the energy. ' +
      'Capacity is about 0.14 N patterns for N cells (here N = ' + N + ', so about ' + Math.round(0.138 * N) + ').' + (paper(fig) ? '' : ' Click a cell to flip it.'), 'nr-dim');
    function thumb(p, parent) {
      var box = h('div', 'nr-thumb', parent);
      var sv = s('svg', { viewBox: '0 0 ' + w * 4 + ' ' + hh * 4, class: 'nr-svg' }, box);
      p.v.forEach(function (v, i) { if (v > 0) s('rect', { x: (i % w) * 4, y: Math.floor(i / w) * 4, width: 4, height: 4, class: 'nr-px' }, sv); });
      h('span', 'nr-thumblab', box, p.name);
      var bar = h('span', 'nr-mbar', box);
      return { box: box, bar: h('span', null, bar), lab: h('span', 'nr-dim', box) };
    }
    var thumbs = [];
    function drawGallery() {
      clear(gallery); thumbs = pats.map(function (p) { return thumb(p, gallery); });
      if (extra) h('div', 'nr-thumb nr-more', gallery, '+ ' + extra + ' random');
    }
    function draw() {
      clear(grid);
      s('rect', { x: 0, y: 0, width: w * 10, height: hh * 10, class: 'nr-gridbg' }, grid);
      state.forEach(function (v, i) {
        var c = s('rect', { x: (i % w) * 10 + 0.6, y: Math.floor(i / w) * 10 + 0.6, width: 8.8, height: 8.8, rx: 1.4,
          class: v > 0 ? 'nr-px' : 'nr-off' }, grid);
        if (!paper(fig)) c.addEventListener('click', function () { stop(); state[i] = -state[i]; energy = [E()]; sweeps = 0; draw(); });
      });
      var best = null, bm = 0;
      pats.forEach(function (p, q) {
        var m = ovl(p);
        thumbs[q].bar.style.width = Math.abs(m) * 100 + '%';
        thumbs[q].bar.className = m < 0 ? 'nr-neg' : '';
        thumbs[q].lab.textContent = 'm ' + m.toFixed(2);
        if (Math.abs(m) > Math.abs(bm)) { bm = m; best = p; }
      });
      var settled = sweeps > 0 && energy.length > 1 && energy[energy.length - 1] === energy[energy.length - 2];
      status.textContent = (sweeps ? 'sweep ' + sweeps + (settled ? ', settled: ' : ': ') : 'the cue: ') +
        (Math.abs(bm) > 0.95 ? (bm < 0 ? 'the inverse of ' : '') + best.name + (bm < 0 ? ' (also a stored minimum)' : sweeps ? ' recalled' : ' nearly')
          : settled ? 'a spurious state, no stored pattern (closest ' + best.name + ', m ' + bm.toFixed(2) + ')'
          : 'closest ' + (best ? best.name : '-') + ', m ' + bm.toFixed(2));
      status.classList.toggle('nr-bad', settled && Math.abs(bm) <= 0.95);
      clear(spark);
      if (energy.length > 1) {
        var lo = Math.min.apply(null, energy), hi = Math.max.apply(null, energy), span = hi - lo || 1;
        s('polyline', { points: energy.map(function (e, q) { return (4 + q / Math.max(1, energy.length - 1) * 192).toFixed(1) + ',' + (6 + (hi - e) / span * 26).toFixed(1); }).join(' '), class: 'nr-trace', stroke: 'var(--nr-pull)' }, spark);
      }
      s('text', { x: 4, y: 38, class: 'nr-tick' }, spark, 'energy by sweep');
      return settled;
    }
    function stop() { if (timer) { clearInterval(timer); timer = null; } }
    function run() {
      stop();
      timer = setInterval(function () { sweep(); if (draw() || sweeps > 30) stop(); }, reduce ? 0 : 380);
    }
    function reset() { stop(); stored = pats.slice(); for (var i = 0; i < extra; i++) stored.push(randomPattern(i)); train(); makeCue(); drawGallery(); draw(); }
    if (!paper(fig)) {
      button(ctl, '▶ recall', 'run updates until the state settles', run);
      button(ctl, 'step', 'one sweep of updates', function () { stop(); sweep(); draw(); });
      button(ctl, 'new cue', 'reset the cue', function () { stop(); makeCue(); draw(); });
      slider(ctl, 'noise', 0, 0.5, 0.01, flip, function (v, out) { flip = v; out.textContent = pct(v); });
      slider(ctl, 'extra memories', 0, Math.round(N * 0.3), 1, 0, function (v, out) { extra = v; out.textContent = (pats.length + v) + ' stored'; if (Wt) reset(); });
    } else ctl.remove();
    reset();
    if (paper(fig)) {                          // print: the cue beside the settled state
      var cueState = state.slice();
      for (var q = 0; q < 30 && sweep(); q++);
      var pair = h('div', 'nr-pair'), c1 = h('div', null, pair), c3 = h('div', null, pair);
      main.insertBefore(pair, grid);
      h('div', 'nr-dim nr-small', c1, 'the cue');
      var c2 = s('svg', { viewBox: '0 0 ' + (w * 10) + ' ' + (hh * 10), class: 'nr-svg nr-grid' }, c1);
      c3.appendChild(grid); h('div', 'nr-dim nr-small', c3, 'after recall');
      s('rect', { x: 0, y: 0, width: w * 10, height: hh * 10, class: 'nr-gridbg' }, c2);
      cueState.forEach(function (v, i) { s('rect', { x: (i % w) * 10 + 0.6, y: Math.floor(i / w) * 10 + 0.6, width: 8.8, height: 8.8, class: v > 0 ? 'nr-px' : 'nr-off' }, c2); });
      draw();
    }
  }

  /* ---- retention: recall probability under reviews ------------------------------------------------------ */
  function retention(fig, d) {
    var horizon = d.horizon || 60, target = d.target || 0.9, G = (d.model && d.model.gain) || 5;
    var items = d.items.map(function (it) { return { name: it.name, s0: it.s0 || 1, reviews: it.reviews.slice().sort(function (a, b) { return a - b; }), color: it.color }; });
    var edit = items.findIndex(function (it) { return it.name === d.editable; });
    function R(t, S) { return 1 / (1 + t / (9 * S)); }
    function run(it) {            // the curve as segments, and the stability after each review
      var S = it.s0, last = it.reviews[0] || 0, segs = [], marks = [];
      it.reviews.forEach(function (t, q) {
        if (q === 0) { marks.push({ t: t, r: 1, S: S }); return; }
        var r = R(t - last, S);
        segs.push({ a: last, b: t, S: S });
        S = S * (1 + G * Math.pow(S, -0.2) * (Math.exp(3 * (1 - r)) - 1));
        marks.push({ t: t, r: r, S: S }); last = t;
      });
      segs.push({ a: last, b: horizon, S: S });
      return { segs: segs, marks: marks, S: S, end: R(horizon - last, S) };
    }
    head(fig, 'RETENTION', d.title, items.map(function (it, i) { return [it.name, col(i, it.color)]; }));
    var ctl = h('div', 'nr-ctl', fig);
    var W = 640, H = 240, L = 44, B = 206, T = 14, Rr = 626;
    var svg = s('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'nr-svg nr-ret', role: 'img' }, fig);
    var tab = h('table', 'nr-tab nr-ret-tab', fig);
    note(fig, d.note);
    note(fig, 'Model: recall R = (1 + t / 9S)^-1, the power-law curve FSRS uses; a review multiplies stability S by more when ' +
      'recall had fallen further (a desirable difficulty), and by almost nothing when it is massed. Shape only; not fitted to anyone.', 'nr-dim');
    var X = function (t) { return L + t / horizon * (Rr - L); }, Y = function (r) { return B - r * (B - T); };
    function draw() {
      clear(svg); clear(tab);
      for (var q = 0; q <= 4; q++) {
        s('line', { x1: L, x2: Rr, y1: Y(q / 4), y2: Y(q / 4), class: 'nr-gridline' }, svg);
        s('text', { x: L - 6, y: Y(q / 4) + 3, class: 'nr-tick', 'text-anchor': 'end' }, svg, q * 25 + '%');
      }
      var st = niceStep(horizon);
      for (var t = 0; t <= horizon; t += st) s('text', { x: X(t), y: B + 16, class: 'nr-tick', 'text-anchor': 'middle' }, svg, t + (t ? '' : ' days'));
      s('line', { x1: L, x2: Rr, y1: Y(target), y2: Y(target), class: 'nr-chance' }, svg);
      s('text', { x: Rr, y: Y(target) - 4, class: 'nr-tick', 'text-anchor': 'end' }, svg, 'target ' + pct(target));
      s('text', { x: 6, y: 10, class: 'nr-tick' }, svg, 'recall');
      var tr = h('tr', null, h('thead', null, tab));
      ['', 'reviews', 'stability at the end', 'recall at day ' + horizon].forEach(function (x) { h('th', null, tr, x); });
      var tb = h('tbody', null, tab);
      items.forEach(function (it, i) {
        var res = run(it), c = col(i, it.color), pts = [];
        res.segs.forEach(function (sg) {
          for (var q = 0; q <= 40; q++) { var tt = sg.a + (sg.b - sg.a) * q / 40; pts.push(X(tt).toFixed(1) + ',' + Y(R(tt - sg.a, sg.S)).toFixed(1)); }
        });
        s('polyline', { points: pts.join(' '), class: 'nr-trace', stroke: c }, svg);
        res.marks.forEach(function (mk, q) {
          var dot = s('circle', { cx: X(mk.t), cy: Y(q ? mk.r : 1), r: 4, fill: c, class: 'nr-dot' + (i === edit ? ' nr-edit' : '') }, svg);
          s('title', {}, dot, it.name + ': review at day ' + (+mk.t.toFixed(1)) + (q ? ', recall had fallen to ' + pct(mk.r) : '') + '; stability now ' + mk.S.toFixed(1) + ' days');
          if (i === edit && q && !paper(fig)) dot.addEventListener('click', function (ev) { ev.stopPropagation(); it.reviews.splice(q, 1); draw(); });
        });
        var row = h('tr', null, tb);
        var sw = h('span', 'nr-sw', h('td', null, row)); sw.style.setProperty('--k', c);
        row.firstChild.appendChild(document.createTextNode(' ' + it.name));
        h('td', null, row, String(it.reviews.length));
        h('td', null, row, res.S.toFixed(1) + ' days');
        h('td', res.end < target ? 'nr-badtxt' : null, row, pct(res.end));
      });
    }
    if (edit >= 0 && !paper(fig)) {
      h('span', 'nr-dim', ctl, 'click the plot to add a review to ' + items[edit].name + '; click one of its dots to remove it');
      button(ctl, 'reset', 'restore the reviews', function () { items[edit].reviews = d.items[edit].reviews.slice().sort(function (a, b) { return a - b; }); draw(); });
      svg.addEventListener('click', function (ev) {
        var pt = svg.createSVGPoint(); pt.x = ev.clientX; pt.y = ev.clientY;
        var p = pt.matrixTransform(svg.getScreenCTM().inverse()), t = (p.x - L) / (Rr - L) * horizon;
        if (t <= 0 || t > horizon) return;
        items[edit].reviews.push(+t.toFixed(1)); items[edit].reviews.sort(function (a, b) { return a - b; }); draw();
      });
      svg.classList.add('nr-clickable');
    } else ctl.remove();
    draw();
  }

  /* ---- rhythm: a cycle of modes --------------------------------------------------------------------------- */
  function rhythm(fig, d) {
    var phases = d.phases, streams = d.streams || [], marks = d.marks || [];
    head(fig, 'RHYTHM', d.title, phases.map(function (p, i) { return [p.label, col(i, p.color)]; }));
    var ctl = h('div', 'nr-ctl', fig);
    var body = h('div', 'nr-body nr-rh-body', fig);
    var dial = s('svg', { viewBox: '-110 -110 220 220', class: 'nr-svg nr-dial', role: 'img' }, body);
    var side = h('div', 'nr-side', body);
    var strip = s('svg', { viewBox: '0 0 380 ' + (30 + streams.length * 34), class: 'nr-svg nr-strip', role: 'img' }, side);
    var mode = h('div', 'nr-mode', side);
    note(fig, d.note);
    var phase = d.start || 0, timer = null;
    function at(deg, rad) { var a = (deg - 90) * Math.PI / 180; return [Math.cos(a) * rad, Math.sin(a) * rad]; }
    function arc(a0, a1, r0, r1) {
      var big = (a1 - a0) % 360 > 180 ? 1 : 0, p0 = at(a0, r1), p1 = at(a1, r1), p2 = at(a1, r0), p3 = at(a0, r0);
      return 'M' + p0 + 'A' + r1 + ',' + r1 + ' 0 ' + big + ' 1 ' + p1 + 'L' + p2 + 'A' + r0 + ',' + r0 + ' 0 ' + big + ' 0 ' + p3 + 'Z';
    }
    function cur() { return phases.findIndex(function (p) { var a = ((phase % 360) + 360) % 360; return p.from <= p.to ? a >= p.from && a < p.to : a >= p.from || a < p.to; }); }
    function draw() {
      clear(dial); clear(strip); clear(mode);
      var ci = cur();
      phases.forEach(function (p, i) {
        var to = p.to > p.from ? p.to : p.to + 360;
        s('path', { d: arc(p.from, to, 62, 96), fill: col(i, p.color), class: 'nr-arc' + (i === ci ? ' nr-cur' : '') }, dial);
        var md = ((p.from + to) / 2) % 360, mid = at(md, 79), rot = md > 90 && md < 270 ? md - 180 : md;
        s('text', { x: mid[0], y: mid[1] + 3, class: 'nr-arclab', 'text-anchor': 'middle',
          transform: 'rotate(' + rot + ' ' + mid[0].toFixed(1) + ' ' + mid[1].toFixed(1) + ')' }, dial, p.label);
      });
      for (var q = 0; q < 360; q += 90) {
        var a = at(q, 100), b = at(q, 106), tx = at(q, 108);
        s('line', { x1: a[0], y1: a[1], x2: b[0], y2: b[1], class: 'nr-axis' }, dial);
      }
      marks.forEach(function (m) { var p = at(m.at, 58); s('circle', { cx: p[0], cy: p[1], r: 3, class: 'nr-mark' }, dial); });
      var hand = at(phase, 98);
      s('line', { x1: 0, y1: 0, x2: hand[0], y2: hand[1], class: 'nr-hand' }, dial);
      s('circle', { cx: 0, cy: 0, r: 4, class: 'nr-hub' }, dial);
      s('text', { x: 0, y: 22, class: 'nr-tick', 'text-anchor': 'middle' }, dial, Math.round(((phase % 360) + 360) % 360) + '°');

      // strip: each stream as a cosine bump peaking at its phase, over one cycle
      var X = function (a) { return 92 + a / 360 * 280; };
      phases.forEach(function (p, i) {
        var to = p.to > p.from ? p.to : p.to + 360;
        [[p.from, Math.min(to, 360)], to > 360 ? [0, to - 360] : null].forEach(function (seg) {
          if (seg) s('rect', { x: X(seg[0]), y: 4, width: X(seg[1]) - X(seg[0]), height: 18 + streams.length * 34, fill: col(i, p.color), class: 'nr-band' }, strip);
        });
      });
      streams.forEach(function (st, k) {
        var y0 = 22 + k * 34 + 28, pts = [];
        for (var a = 0; a <= 360; a += 6) pts.push(X(a).toFixed(1) + ',' + (y0 - (0.5 + 0.5 * Math.cos((a - st.peak) * Math.PI / 180)) * 24).toFixed(1));
        s('polyline', { points: pts.join(' '), class: 'nr-trace', stroke: 'var(--nr-ink2)' }, strip);
        s('text', { x: 86, y: y0 - 8, class: 'nr-slab', 'text-anchor': 'end' }, strip, st.name);
        var a2 = ((phase % 360) + 360) % 360, v = 0.5 + 0.5 * Math.cos((a2 - st.peak) * Math.PI / 180);
        s('circle', { cx: X(a2), cy: y0 - v * 24, r: 3.5, class: 'nr-hub' }, strip);
      });
      var a3 = ((phase % 360) + 360) % 360;
      s('line', { x1: X(a3), x2: X(a3), y1: 2, y2: 24 + streams.length * 34, class: 'nr-cursor' }, strip);
      if (d.period) h('div', 'nr-dim nr-small', mode, d.period);
      if (ci >= 0) {
        var pp = phases[ci];
        var t = h('div', 'nr-modename', mode, pp.label); t.style.setProperty('--k', col(ci, pp.color));
        if (pp.note) h('div', 'nr-modenote', mode, pp.note);
      }
      marks.forEach(function (m) { if (Math.abs(((a3 - m.at + 540) % 360) - 180) > 160) h('div', 'nr-dim', mode, m.label); });
    }
    function stop() { if (timer) { clearInterval(timer); timer = null; } }
    if (!paper(fig)) {
      var play = button(ctl, '▶', 'play the cycle', function () {
        if (timer) { stop(); play.textContent = '▶'; return; }
        play.textContent = '❚❚';
        timer = setInterval(function () { phase = (phase + 3) % 360; rng2.value = phase; draw(); }, reduce ? 120 : 40);
      });
      var rng2 = slider(ctl, 'phase', 0, 359, 1, phase, function (v, out) { phase = v; out.textContent = v + '°'; draw(); });
    } else ctl.remove();
    draw();
  }

  var VIEWS = { engram: engram, attractor: attractor, retention: retention, rhythm: rhythm };
  function build(fig) {
    var src = fig.querySelector(':scope > script[type="application/json"]');
    var kind = fig.getAttribute('data-neuro');
    if (!src || !VIEWS[kind]) return;
    fig.classList.add('nr', 'nr-' + kind, 'nr-ready');
    var cap = fig.querySelector(':scope > figcaption');
    try { VIEWS[kind](fig, JSON.parse(src.textContent)); }
    catch (err) { h('pre', 'nr-error', fig, 'neuro ' + kind + ': ' + String(err.message || err)); }
    if (cap) fig.appendChild(cap);
    fig.neuro = true;
  }
  function boot() {
    Array.prototype.forEach.call(document.querySelectorAll('[data-neuro]'), function (f) { if (!f.neuro) build(f); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
  window.neuro = { boot: boot };
})();
