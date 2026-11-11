/* pregel: LangGraph's runtime drawn from data. Five views over three small JSON formats (FORMAT in the README):
   superstep, fanout and reducer read one pregel trace; checkpoints reads a thread's history; interrupt reads a
   hand-written run script. Each figure is <figure data-pregel="kind"><script type="application/json">.
   No eval, no innerHTML, no inline handlers: text goes in as text, so a page's CSP needs nothing extra. */
(function () {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg';
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var figN = 0;

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
  function fmt(v, max) {
    max = max || 56;
    var t = v === undefined ? '-' : typeof v === 'string' ? JSON.stringify(v) : JSON.stringify(v);
    if (t === undefined) t = String(v);
    return t.length > max ? t.slice(0, max - 1) + '…' : t;
  }
  function ver(v) {
    if (v === undefined || v === null) return undefined;
    if (typeof v === 'string' && v.indexOf('.') > 0) return parseInt(v, 10);
    return +v;
  }
  function pad10(n) { var t = String(n); while (t.length < 10) t = '0' + t; return t; }
  function short(id) { return id ? String(id).slice(-6) : ''; }
  function badge(kind, parent) { return h('span', 'pg-badge pg-' + kind, parent, kind === 'pull' ? 'PULL' : 'PUSH'); }
  function head(fig, eyebrow, title) {
    var hd = h('div', 'pg-head', fig);
    var tt = h('div', 'pg-title', hd);
    h('span', 'pg-eyebrow', tt, eyebrow);
    h('span', 'pg-name', tt, title || '');
    return h('div', 'pg-legend', hd);
  }
  function key(parent, cls, text) { var k = h('span', 'pg-li', parent); h('span', 'pg-sw ' + cls, k); k.appendChild(document.createTextNode(text)); return k; }
  function paper(fig) { return fig.hasAttribute('data-paper') || (window.matchMedia && matchMedia('print').matches); }

  // the merge order: LangGraph sorts a step's tasks by task_path_str(path) before it applies their writes
  function pathKey(t, pushIndex) {
    if (typeof t.path === 'string') return t.path;
    if (Array.isArray(t.path)) return pathStr(t.path);
    return t.kind === 'push' ? '~__pregel_push, ' + pad10(pushIndex) : '~__pregel_pull, ' + t.name;
  }
  function pathStr(x) {
    if (Array.isArray(x)) return '~' + x.map(pathStr).join(', ');
    return typeof x === 'number' ? pad10(x) : String(x);
  }
  function ordered(tasks) {
    var i = 0;
    var keyed = (tasks || []).map(function (t, j) { return { t: t, k: pathKey(t, t.kind === 'push' ? i++ : 0), j: j }; });
    keyed.sort(function (a, b) { return a.k < b.k ? -1 : a.k > b.k ? 1 : a.j - b.j; });
    return keyed.map(function (x, n) { x.t._order = n + 1; x.t._key = x.k; return x.t; });
  }
  function pushIndex(t) {
    var m = /__pregel_push, 0*(\d+)/.exec(t._key || '');
    return m ? +m[1] : null;
  }

  // the stepper every view shares: |< < play > >|, a scrubber, the arrow keys
  function controls(fig, n, show, label) {
    var C = { at: 0, timer: null };
    var bar = h('div', 'pg-ctl', fig);
    function mk(t, aria, fn) { var b = h('button', 'pg-btn', bar, t); b.type = 'button'; b.setAttribute('aria-label', aria); b.addEventListener('click', fn); return b; }
    function go(i) { C.at = Math.max(0, Math.min(n - 1, i)); C.scrub.value = C.at; C.lab.textContent = label(C.at); show(C.at); }
    function stop() { if (C.timer) { clearInterval(C.timer); C.timer = null; } C.play.textContent = 'play'; C.play.classList.remove('is-on'); }
    mk('|<', 'to the start', function () { stop(); go(0); });
    mk('<', 'step back', function () { stop(); go(C.at - 1); });
    C.play = mk('play', 'play', function () {
      if (C.timer) { stop(); return; }
      if (C.at >= n - 1) go(0);
      C.play.textContent = 'pause'; C.play.classList.add('is-on');
      C.timer = setInterval(function () { if (C.at >= n - 1) stop(); else go(C.at + 1); }, reduce ? 1800 : 1200);
    });
    mk('>', 'step forward', function () { stop(); go(C.at + 1); });
    mk('>|', 'to the end', function () { stop(); go(n - 1); });
    C.scrub = h('input', 'pg-scrub', bar);
    C.scrub.type = 'range'; C.scrub.min = 0; C.scrub.max = Math.max(0, n - 1); C.scrub.step = 1; C.scrub.value = 0;
    C.scrub.setAttribute('aria-label', 'position');
    C.scrub.addEventListener('input', function () { stop(); go(+C.scrub.value); });
    C.lab = h('span', 'pg-pos', bar);
    fig.tabIndex = fig.tabIndex >= 0 ? fig.tabIndex : 0;
    fig.addEventListener('keydown', function (ev) {
      if (ev.target.tagName === 'INPUT' || ev.target.tagName === 'BUTTON') return;
      if (ev.key === 'ArrowRight') { ev.preventDefault(); stop(); go(C.at + 1); }
      if (ev.key === 'ArrowLeft') { ev.preventDefault(); stop(); go(C.at - 1); }
    });
    C.go = go;
    return C;
  }

  // ---- the trace, read once: each node's triggers, each step's tasks in merge order ---------------------------------
  function readTrace(T) {
    T.steps = T.steps || [];
    T.channels = T.channels || {};
    T.defer = T.defer || [];
    var trig = {};
    T.steps.forEach(function (st) {
      st.tasks = ordered(st.tasks);
      st.tasks.forEach(function (t) {
        if (t.kind === 'pull') (t.triggers || []).forEach(function (c) { (trig[t.name] = trig[t.name] || {})[c] = 1; });
      });
    });
    // a PUSH task's Send: the i-th Send written in the step before makes PUSH task #i
    T.steps.forEach(function (st, i) {
      var prev = T.steps[i - 1], sends = [];
      if (prev) prev.tasks.forEach(function (t) { (t.writes || []).forEach(function (w) { if (w[0] === '__pregel_tasks') sends.push({ from: t.name, arg: (w[1] || {}).arg, node: (w[1] || {}).node }); }); });
      st.tasks.forEach(function (t) { if (t.kind === 'push' && !t.send) { var k = pushIndex(t); if (k !== null && sends[k]) t.send = sends[k]; } });
    });
    T.triggers = {};
    Object.keys(trig).forEach(function (k) { T.triggers[k] = Object.keys(trig[k]); });
    var names = {};
    T.steps.forEach(function (st) {
      st.tasks.forEach(function (t) { names[t.name] = 1; });
      Object.keys(st.versions_seen || {}).forEach(function (k) { names[k] = 1; });
    });
    T.nodes = Object.keys(names);
    return T;
  }
  function isReducer(T, c) {
    var ch = T.channels[c] || {};
    return !!ch.reducer || ch.type === 'BinaryOperatorAggregate';
  }

  // why a node does or does not run next: a trigger channel holding a value and newer than the node last saw
  function why(T, st, node) {
    var cv = st.channel_versions || {}, seen = (st.versions_seen || {})[node] || {};
    var avail = st.available ? {} : null;
    (st.available || []).forEach(function (c) { avail[c] = 1; });
    var next = (st.next || []).indexOf(node) >= 0;
    var out = [];
    (T.triggers[node] || []).forEach(function (c) {
      var v = ver(cv[c]), w = ver(seen[c]);
      if (v === undefined) return;
      var newer = w === undefined || v > w, has = !avail || !!avail[c];
      out.push({ c: c, v: v, w: w, newer: newer, has: has, fires: newer && has });
    });
    var fires = out.some(function (x) { return x.fires; });
    var deferred = T.defer.indexOf(node) >= 0 && fires && !next;
    var sent = next && !fires;
    return { next: next, list: out, fires: fires, deferred: deferred, sent: sent };
  }

  // ---- :::superstep ------------------------------------------------------------------------------------------------------
  function superstep(fig, T) {
    readTrace(T);
    var lg = head(fig, 'pregel superstep', T.title);
    key(lg, 'pg-sw-pull', 'PULL task'); key(lg, 'pg-sw-push', 'PUSH task (a Send)');
    key(lg, 'pg-sw-upd', 'channel updated'); key(lg, 'pg-sw-next', 'runs next');
    var G = null;
    if (T.graph) {
      var gwrap = h('div', 'pg-graph', fig);
      var gd = h('div', 'lg', gwrap);
      gd.setAttribute('data-loopgraph', ''); gd.setAttribute('data-bare', '');
      if (paper(fig)) gd.setAttribute('data-collapse', '');
      var js = h('script', '', gd); js.type = 'application/json';
      js.textContent = JSON.stringify(T.graph);
      gd.addEventListener('loopgraph:ready', function (ev) { G = ev.detail; if (C) light(C.at); });
      if (window.loopgraph) window.loopgraph.boot();
    }
    var note = h('p', 'pg-note', fig);
    var grid = h('div', 'pg-grid', fig);
    var pT = h('section', 'pg-panel pg-tasks', grid), pC = h('section', 'pg-panel pg-chans', grid), pN = h('section', 'pg-panel pg-next', grid);
    function light(i) {
      if (!G) return;
      var st = T.steps[i], prev = T.steps[i - 1], on = [];
      for (var j = 0; j <= i; j++) T.steps[j].tasks.forEach(function (t) { on.push(t.name); });
      G.light({ cur: st.tasks.map(function (t) { return t.name; }), prev: prev ? prev.tasks.map(function (t) { return t.name; }) : ['__start__'],
                on: on, next: st.next || [] });
    }
    function show(i) {
      var st = T.steps[i], prev = T.steps[i - 1] || { channel_versions: {}, values: {} };
      note.textContent = st.note || '';
      note.hidden = !st.note;
      // tasks
      pT.textContent = '';
      h('h4', 'pg-ph', pT, st.step < 0 ? 'the input' : 'tasks that ran, in merge order');
      if (st.step < 0 || !st.tasks.length) {
        var p = h('p', 'pg-input', pT);
        h('span', 'pg-dim', p, 'written to __start__: ');
        h('code', '', p, fmt(st.input, 120));
      }
      st.tasks.forEach(function (t) {
        var r = h('div', 'pg-task' + (t.status && t.status !== 'ok' ? ' is-' + t.status : ''), pT);
        var top = h('div', 'pg-task-top', r);
        h('span', 'pg-ord', top, String(t._order));
        badge(t.kind, top);
        h('b', 'pg-tname', top, t.name);
        if (t.status && t.status !== 'ok') h('span', 'pg-status', top, t.status);
        var tr = h('div', 'pg-sub', r);
        tr.appendChild(document.createTextNode(t.kind === 'push' ? 'Send #' + pushIndex(t) + (t.send && t.send.from ? ' from ' + t.send.from : '') + ': ' : 'triggered by '));
        h('code', '', tr, t.kind === 'push' ? fmt((t.send || {}).arg, 40) : (t.triggers || []).join(', ') || '-');
        var ws = h('ul', 'pg-writes', r);
        (t.writes || []).forEach(function (w) {
          var li = h('li', w[0] === '__pregel_tasks' ? 'is-send' : w[0].indexOf('branch:') === 0 ? 'is-branch' : '', ws);
          h('code', 'pg-ch', li, w[0] === '__pregel_tasks' ? 'Send' : w[0]);
          h('code', 'pg-val', li, w[0] === '__pregel_tasks' ? (w[1] && w[1].node ? w[1].node + ' ' + fmt(w[1].arg, 36) : fmt(w[1], 36)) : fmt(w[1], 44));
        });
        if (!(t.writes || []).length) h('li', 'pg-dim', ws, 'no writes');
      });
      // channels
      pC.textContent = '';
      h('h4', 'pg-ph', pC, 'channels after the step');
      var tb = h('table', 'pg-table', pC), thr = h('tr', '', h('thead', '', tb));
      ['channel', 'version', 'value'].forEach(function (x) { h('th', '', thr, x); });
      var body = h('tbody', '', tb);
      var cv = st.channel_versions || {}, pv = prev.channel_versions || {};
      var avail = {}; (st.available || Object.keys(cv)).forEach(function (c) { avail[c] = 1; });
      var chans = Object.keys(cv).sort(function (a, b) { return rankC(a) - rankC(b) || (a < b ? -1 : 1); });
      var writers = {};
      st.tasks.forEach(function (t) { (t.writes || []).forEach(function (w) { (writers[w[0]] = writers[w[0]] || []).push(t.name); }); });
      chans.forEach(function (c) {
        var upd = (st.updated || []).indexOf(c) >= 0;
        var tr2 = h('tr', (upd ? 'is-upd' : '') + (avail[c] ? '' : ' is-empty') + (/^(branch:|__)/.test(c) ? ' is-sys' : ''), body);
        var td = h('td', '', tr2);
        h('code', '', td, c);
        var ty = (T.channels[c] || {}).type;
        if (ty) h('span', 'pg-type', td, ty + ((T.channels[c] || {}).reducer ? ' (' + T.channels[c].reducer + ')' : ''));
        var tv = h('td', 'pg-ver', tr2);
        var a = ver(pv[c]), b = ver(cv[c]);
        tv.textContent = upd && a !== undefined && a !== b ? a + ' → ' + b : String(b);
        var tvv = h('td', '', tr2);
        if (st.values && c in st.values) h('code', 'pg-val', tvv, fmt(st.values[c], 40));
        else h('span', 'pg-dim', tvv, avail[c] ? 'set' : 'empty');
        if (writers[c]) h('span', 'pg-by', tvv, 'by ' + writers[c].join(', '));
      });
      // versions_seen and the next step
      pN.textContent = '';
      h('h4', 'pg-ph', pN, 'versions_seen, and what runs next');
      var nx = h('p', 'pg-nextline', pN);
      h('span', 'pg-dim', nx, 'next: ');
      if (!(st.next || []).length) h('b', '', nx, 'nothing; the run ends');
      (st.next || []).forEach(function (x) { h('span', 'pg-chip pg-chip-next', nx, x); });
      var tb2 = h('table', 'pg-table pg-seen', pN), th2 = h('tr', '', h('thead', '', tb2));
      ['node', 'trigger: version / seen', ''].forEach(function (x) { h('th', '', th2, x); });
      var b2 = h('tbody', '', tb2);
      T.nodes.filter(function (n) { return n !== '__start__' || st.step <= 0; }).forEach(function (n) {
        var W = why(T, st, n);
        var tr3 = h('tr', W.next ? 'is-next' : W.deferred ? 'is-wait' : '', b2);
        h('code', '', h('td', '', tr3), n);
        var cell = h('td', '', tr3);
        if (!W.list.length) h('span', 'pg-dim', cell, T.triggers[n] ? (T.triggers[n].join(', ') + ': not written yet') : 'no trigger channel: runs only from a Send');
        W.list.forEach(function (x) {
          var c = h('span', 'pg-trig' + (x.fires ? ' is-fire' : x.newer ? ' is-stale' : ''), cell);
          h('code', '', c, x.c);
          c.appendChild(document.createTextNode(' ' + x.v + ' / ' + (x.w === undefined ? '-' : x.w)));
        });
        var r = h('td', 'pg-why', tr3);
        r.textContent = W.next ? (W.sent ? 'runs: a Send' : 'runs: newer, and set') : W.deferred ? 'deferred: waits until nothing else runs'
          : W.list.some(function (x) { return x.newer && !x.has; }) ? 'newer, but empty' : '';
      });
      light(i);
    }
    function rankC(c) { return /^__/.test(c) ? 3 : /^branch:/.test(c) ? 2 : 1; }
    var C = paper(fig) ? null : controls(fig, T.steps.length, show, function (i) {
      var st = T.steps[i]; return 'step ' + st.step + ' · ' + (st.source || '') + '  (' + (i + 1) + ' of ' + T.steps.length + ')';
    });
    if (C) C.go(0); else show(T.steps.length - 1);
  }

  // ---- :::fanout ---------------------------------------------------------------------------------------------------------
  function fanout(fig, T) {
    readTrace(T);
    var lg = head(fig, 'send fan-out', T.title);
    key(lg, 'pg-sw-pull', 'PULL'); key(lg, 'pg-sw-push', 'PUSH from a Send'); key(lg, 'pg-sw-wait', 'deferred, waiting');
    // the start task only copies the input in: leave its column out
    var steps = T.steps.filter(function (st) { return st.tasks.some(function (t) { return t.name !== '__start__'; }); });
    var CW = 156, GAP = 34, CH = 46, VG = 10, TOP = 34, PAD = 14;
    // the deferred nodes' waits: from the step after their trigger first held a value to the step before they ran
    var waits = {};
    T.defer.forEach(function (d) {
      var ranAt = null;
      T.steps.forEach(function (st) { st.tasks.forEach(function (t) { if (t.name === d && ranAt === null) ranAt = st.step; }); });
      var trg = T.triggers[d] || [], from = null;
      T.steps.forEach(function (st) {
        if (from === null && st.step < ranAt && trg.some(function (c) { return (st.updated || []).indexOf(c) >= 0; })) from = st.step + 1;
      });
      if (from !== null && ranAt !== null) for (var k = from; k < ranAt; k++) (waits[k] = waits[k] || []).push(d);
    });
    var cols = steps.map(function (st, i) {
      var cards = st.tasks.map(function (t) { return { t: t }; });
      (waits[st.step] || []).forEach(function (d) { cards.push({ wait: d }); });
      var merges = [];
      st.tasks.forEach(function (t) { (t.writes || []).forEach(function (w) { if (isReducer(T, w[0])) merges.push({ c: w[0], v: w[1], t: t }); }); });
      return { st: st, x: PAD + i * (CW + GAP), cards: cards, merges: merges };
    });
    var maxCards = Math.max.apply(null, cols.map(function (c) { return c.cards.length; }));
    var mergeY = TOP + maxCards * (CH + VG) + 22;
    var maxMerge = Math.max.apply(null, cols.map(function (c) { return c.merges.length; }).concat([0]));
    var H = mergeY + (maxMerge ? 30 + maxMerge * 17 : 0) + PAD;
    var W = PAD * 2 + cols.length * CW + (cols.length - 1) * GAP;
    var wrap = h('div', 'pg-scroll', fig);
    var svg = s('svg', { 'class': 'pg-svg', viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'img', 'aria-label': (T.title || 'fan-out') + ': tasks by superstep' }, wrap);
    var defs = s('defs', {}, svg), id = 'pg' + (++figN);
    ['send', 'hot'].forEach(function (k) {
      var m = s('marker', { id: id + '-' + k, viewBox: '0 0 8 8', refX: 7, refY: 4, markerWidth: 7, markerHeight: 7, orient: 'auto-start-reverse' }, defs);
      s('path', { d: 'M0 0 L8 4 L0 8 z', 'class': 'pg-mk-' + k }, m);
    });
    var gA = s('g', { 'class': 'pg-arrows' }, svg), gC = s('g', {}, svg);
    var cardAt = {};
    cols.forEach(function (col, ci) {
      s('text', { x: col.x, y: 16, 'class': 'pg-colh' }, gC, 'step ' + col.st.step);
      s('text', { x: col.x + CW, y: 16, 'class': 'pg-colh2', 'text-anchor': 'end' }, gC, col.st.tasks.length + (col.st.tasks.length === 1 ? ' task' : ' tasks, in parallel'));
      col.cards.forEach(function (cd, k) {
        var y = TOP + k * (CH + VG);
        var g = s('g', { 'class': 'pg-card ' + (cd.wait ? 'is-wait' : 'pg-' + cd.t.kind), tabindex: 0 }, gC);
        s('rect', { x: col.x, y: y, width: CW, height: CH, rx: 6, 'class': 'pg-card-box' }, g);
        if (cd.wait) {
          s('text', { x: col.x + 10, y: y + 19, 'class': 'pg-card-name' }, g, cd.wait);
          s('text', { x: col.x + 10, y: y + 35, 'class': 'pg-card-sub' }, g, 'deferred, waiting');
          return;
        }
        var t = cd.t;
        s('rect', { x: col.x, y: y, width: 4, height: CH, rx: 2, 'class': 'pg-card-stripe' }, g);
        s('text', { x: col.x + 12, y: y + 19, 'class': 'pg-card-name' }, g, t.name);
        s('text', { x: col.x + CW - 10, y: y + 19, 'class': 'pg-card-tag', 'text-anchor': 'end' }, g,
          t.kind === 'push' ? 'PUSH #' + pushIndex(t) : 'PULL');
        var sub = t.kind === 'push' ? fmt((t.send || {}).arg, 22) : fmt((t.triggers || []).join(', '), 22).replace(/^"|"$/g, '');
        var sends = (t.writes || []).filter(function (w) { return w[0] === '__pregel_tasks'; }).length;
        if (sends) sub = sends + ' Send' + (sends > 1 ? 's' : '') + ' out';
        s('text', { x: col.x + 12, y: y + 35, 'class': 'pg-card-sub' }, g, sub);
        if (t.ms) {
          var span = Math.max(1, t.ms[1] - t.ms[0]), all = Math.max.apply(null, col.st.tasks.map(function (x) { return x.ms ? x.ms[1] : 1; }));
          s('rect', { x: col.x + 12, y: y + CH - 5, width: (CW - 24) * span / all, height: 2, 'class': 'pg-card-ms' }, g);
        }
        cardAt[col.st.step + ':' + t._order] = { x: col.x, y: y, t: t, g: g, col: ci };
      });
      if (col.merges.length) {
        var mx = col.x, my = mergeY;
        var mg = s('g', { 'class': 'pg-merge' }, gC);
        s('rect', { x: mx, y: my, width: CW, height: 22 + col.merges.length * 17, rx: 6, 'class': 'pg-merge-box' }, mg);
        var chs = {}; col.merges.forEach(function (m) { chs[m.c] = 1; });
        s('text', { x: mx + 10, y: my + 15, 'class': 'pg-merge-h' }, mg, 'gather: ' + Object.keys(chs).join(', '));
        col.merges.forEach(function (m, k) {
          var ty = my + 32 + k * 17;
          var row = s('g', { 'class': 'pg-merge-row', 'data-task': col.st.step + ':' + m.t._order }, mg);
          s('text', { x: mx + 10, y: ty, 'class': 'pg-merge-n' }, row, String(k + 1));
          s('text', { x: mx + 24, y: ty, 'class': 'pg-merge-t' }, row, m.t.name + (m.t.kind === 'push' ? ' #' + pushIndex(m.t) : ''));
          var nm = m.t.name + (m.t.kind === 'push' ? ' #' + pushIndex(m.t) : '');
          s('text', { x: mx + CW - 8, y: ty, 'class': 'pg-merge-v', 'text-anchor': 'end' }, row, fmt(m.v, Math.max(6, Math.floor((CW - 40 - nm.length * 6.4) / 6.6))));
        });
      }
    });
    // Send arrows: the i-th Send written in a step makes PUSH task #i in the next
    var arrows = [];
    cols.forEach(function (col, ci) {
      var nextCol = cols[ci + 1];
      if (!nextCol) return;
      var i = 0;
      col.st.tasks.forEach(function (t) {
        (t.writes || []).forEach(function (w) {
          if (w[0] !== '__pregel_tasks') return;
          var src = cardAt[col.st.step + ':' + t._order];
          var dst = null;
          nextCol.st.tasks.forEach(function (u) { if (u.kind === 'push' && pushIndex(u) === i) dst = cardAt[nextCol.st.step + ':' + u._order]; });
          i++;
          if (!src || !dst) return;
          var x0 = src.x + CW, y0 = src.y + CH / 2, x1 = dst.x - 2, y1 = dst.y + CH / 2, mx2 = (x0 + x1) / 2;
          var p = s('path', { d: 'M' + x0 + ' ' + y0 + ' C' + mx2 + ' ' + y0 + ' ' + mx2 + ' ' + y1 + ' ' + x1 + ' ' + y1, 'class': 'pg-arrow', 'marker-end': 'url(#' + id + '-send)' }, gA);
          arrows.push({ p: p, a: src, b: dst });
        });
      });
    });
    // hover or focus a card: its Sends, its writes in the gather
    Object.keys(cardAt).forEach(function (k) {
      var c = cardAt[k];
      function on(x) {
        c.g.classList.toggle('is-hot', x);
        arrows.forEach(function (a) { if (a.a === c || a.b === c) { a.p.classList.toggle('is-hot', x); a.p.setAttribute('marker-end', 'url(#' + id + '-' + (x ? 'hot' : 'send') + ')'); } });
        Array.prototype.forEach.call(svg.querySelectorAll('.pg-merge-row'), function (r) { if (r.getAttribute('data-task') === k) r.classList.toggle('is-hot', x); });
      }
      c.g.addEventListener('mouseenter', function () { on(true); }); c.g.addEventListener('mouseleave', function () { on(false); });
      c.g.addEventListener('focus', function () { on(true); }); c.g.addEventListener('blur', function () { on(false); });
    });
  }

  // ---- :::reducer --------------------------------------------------------------------------------------------------------
  function fold(red, a, b) {
    if (!/add|concat|sum|extend/.test(red || '')) return undefined;
    if (Array.isArray(a) || Array.isArray(b)) return (Array.isArray(a) ? a : a === undefined ? [] : [a]).concat(b);
    if (typeof a === 'number' && typeof b === 'number') return a + b;
    if (typeof a === 'string' && typeof b === 'string') return a + b;
    if (a === undefined) return b;
    return undefined;
  }
  function reducer(fig, T) {
    readTrace(T);
    var want = fig.getAttribute('data-step'), ch = fig.getAttribute('data-channel');
    var i = 0;
    T.steps.forEach(function (st, j) { if (String(st.step) === want) i = j; });
    var st = T.steps[i], prev = T.steps[i - 1] || { values: {} };
    var info = T.channels[ch] || {}, red = info.reducer || '';
    var lg = head(fig, 'reducer merge', (T.title ? T.title + ': ' : '') + ch + ' at step ' + st.step);
    h('span', 'pg-li', lg, (info.type || 'channel') + (red ? ', reducer ' + red : ''));
    var writes = [];
    st.tasks.forEach(function (t) { (t.writes || []).forEach(function (w) { if (w[0] === ch) writes.push({ t: t, v: w[1] }); }); });
    var row = h('div', 'pg-fold', fig);
    function box(lab, v, cls) {
      var b = h('div', 'pg-fbox ' + (cls || ''), row);
      h('div', 'pg-flab', b, lab);
      h('code', 'pg-fval', b, v === undefined ? '(empty)' : fmt(v, 160));
      return b;
    }
    var before = prev.values ? prev.values[ch] : undefined;
    var acc = [before], boxes = [box('before', before, 'is-before')];
    writes.forEach(function (w, k) {
      h('span', 'pg-op', row, red ? '⊕' : '+');
      var b = h('div', 'pg-fbox pg-w', row);
      var top = h('div', 'pg-flab', b);
      h('span', 'pg-ord', top, String(k + 1));
      badge(w.t.kind, top);
      top.appendChild(document.createTextNode(' ' + w.t.name + (w.t.kind === 'push' ? ' #' + pushIndex(w.t) : '')));
      h('code', 'pg-fval', b, fmt(w.v, 80));
      h('div', 'pg-path', b, w.t._key);
      boxes.push(b);
      acc.push(fold(red, acc[k], w.v));
    });
    h('span', 'pg-op', row, '=');
    var after = st.values ? st.values[ch] : undefined;
    boxes.push(box('after', after, 'is-after'));
    var run = h('p', 'pg-note', fig);
    var ex = h('p', 'pg-explain', fig);
    ex.textContent = 'LangGraph sorts a superstep’s tasks by their path string before it applies any write, so the merge order is fixed: PULL tasks by node name, then PUSH tasks by Send index. When the tasks finished does not matter.';
    var arrival = writes.filter(function (w) { return w.t.ms; }).length === writes.length && writes.length > 1
      ? writes.slice().sort(function (a, b) { return a.t.ms[1] - b.t.ms[1]; }) : null;
    if (arrival) {
      var ar = h('p', 'pg-explain', fig);
      ar.textContent = 'They finished in this order: ' + arrival.map(function (w) { return w.t.name + (w.t.kind === 'push' ? ' #' + pushIndex(w.t) : ''); }).join(', ') + '. The merge ignores it.';
    }
    function show(k) {
      boxes.forEach(function (b, j) { b.classList.toggle('is-on', j <= k); b.classList.toggle('is-cur', j === k); });
      var v = k === 0 ? before : k <= writes.length ? acc[k] : after;
      run.textContent = k === 0 ? 'Start from the value the step began with.'
        : k <= writes.length ? 'After write ' + k + ': ' + (v === undefined ? '(the reducer’s own result)' : fmt(v, 140))
        : 'The channel after the step: ' + fmt(after, 140);
    }
    if (paper(fig)) show(writes.length + 1);
    else controls(fig, writes.length + 2, show, function (k) { return k === 0 ? 'before' : k <= writes.length ? 'write ' + k + ' of ' + writes.length : 'after'; }).go(0);
  }

  // ---- :::checkpoints ----------------------------------------------------------------------------------------------------
  function checkpoints(fig, D) {
    var cps = D.checkpoints || [], by = {}, kids = {};
    cps.forEach(function (c, i) { c._i = i; by[c.id] = c; kids[c.id] = []; });
    var roots = [];
    cps.forEach(function (c) { if (c.parent && by[c.parent]) kids[c.parent].push(c); else roots.push(c); });
    var lane = 0;
    function place(c, l) { c._lane = l; kids[c.id].forEach(function (k, j) { place(k, j === 0 ? l : ++lane); }); }
    roots.forEach(function (r, j) { place(r, j === 0 ? 0 : ++lane); });
    var steps = cps.map(function (c) { return c.step; });
    var smin = Math.min.apply(null, steps), smax = Math.max.apply(null, steps);
    var lg = head(fig, 'checkpoint history', (D.title || '') + (D.thread ? '  thread ' + D.thread : ''));
    ['input', 'loop', 'update', 'fork'].forEach(function (k) { key(lg, 'pg-sw-src pg-src-' + k, k); });
    key(lg, 'pg-sw-irq', 'interrupt'); key(lg, 'pg-sw-head', 'HEAD');
    var span = Math.max(1, smax - smin), stack = span > 4;
    var body = h('div', 'pg-ckrow' + (stack ? ' is-stack' : ''), fig);
    var wrap = h('div', 'pg-scroll', body);
    // columns fitted to the room the tree has: the whole figure when the panel goes underneath
    var room = (fig.clientWidth || 760) - (stack ? 40 : 330);
    var X0 = 60, CW = Math.max(72, Math.min(120, Math.floor((room - 2 * X0) / span))), LH = 72, Y0 = 44;
    var W = X0 * 2 + (smax - smin) * CW, H = Y0 + lane * LH + 46;
    var svg = s('svg', { 'class': 'pg-svg', viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'img', 'aria-label': 'checkpoints by step, forks below' }, wrap);
    for (var st = smin; st <= smax; st++) {
      var x = X0 + (st - smin) * CW;
      s('line', { x1: x, x2: x, y1: 22, y2: H - 8, 'class': 'pg-grid-l' }, svg);
      s('text', { x: x, y: 14, 'class': 'pg-colh', 'text-anchor': 'middle' }, svg, 'step ' + st);
    }
    function pos(c) { return [X0 + (c.step - smin) * CW, Y0 + c._lane * LH]; }
    cps.forEach(function (c) {
      if (!c.parent || !by[c.parent]) return;
      var a = pos(by[c.parent]), b = pos(c);
      var d = a[1] === b[1] ? 'M' + a[0] + ' ' + a[1] + ' L' + b[0] + ' ' + b[1]
        : b[0] > a[0] ? 'M' + (a[0] + 9) + ' ' + a[1] + ' C' + (a[0] + b[0]) / 2 + ' ' + a[1] + ' ' + (a[0] + b[0]) / 2 + ' ' + b[1] + ' ' + (b[0] - 9) + ' ' + b[1]
        : 'M' + a[0] + ' ' + a[1] + ' C' + a[0] + ' ' + (a[1] + b[1]) / 2 + ' ' + (a[0] + b[0]) / 2 + ' ' + b[1] + ' ' + b[0] + ' ' + b[1];   // a fork leaves from the side, clear of its parent's label
      s('path', { d: d, 'class': 'pg-ck-edge' + (a[1] !== b[1] ? ' is-fork' : '') }, svg);
    });
    var panel = h('aside', 'pg-ckpanel', body), els = {};
    cps.forEach(function (c) {
      var p = pos(c), g = s('g', { 'class': 'pg-ck pg-src-' + (c.source || 'loop'), tabindex: 0, role: 'button', 'aria-label': 'checkpoint ' + short(c.id) + ', step ' + c.step + ', ' + c.source }, svg);
      s('circle', { cx: p[0], cy: p[1], r: 13, 'class': 'pg-ck-halo' }, g);
      s('circle', { cx: p[0], cy: p[1], r: 8, 'class': 'pg-ck-dot' }, g);
      s('text', { x: p[0], y: p[1] + 24, 'class': 'pg-ck-id', 'text-anchor': 'middle' }, g, short(c.id));
      var irq = (c.tasks || []).some(function (t) { return (t.interrupts || []).length; });
      if (irq) s('circle', { cx: p[0] + 8, cy: p[1] - 8, r: 4, 'class': 'pg-ck-irq' }, g);
      var pw = (c.pending_writes || []).length;
      if (pw) s('text', { x: p[0] - 11, y: p[1] - 11, 'class': 'pg-ck-pw', 'text-anchor': 'end' }, g, pw + 'w');
      if (c.id === D.head) {
        s('text', { x: p[0], y: p[1] - 17, 'class': 'pg-ck-head', 'text-anchor': 'middle' }, g, 'HEAD');
        g.classList.add('is-head');
      }
      if (c.label) s('text', { x: p[0], y: p[1] + 37, 'class': 'pg-ck-label', 'text-anchor': 'middle' }, g, fmt(c.label, Math.max(8, Math.floor(CW / 6.2))).replace(/^"|"$/g, ''));
      g.addEventListener('click', function () { pick(c); });
      g.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); pick(c); } });
      els[c.id] = g;
    });
    function pick(c) {
      Object.keys(els).forEach(function (k) { els[k].classList.toggle('is-cur', k === c.id); });
      var line = {}; for (var x = c; x; x = by[x.parent]) line[x.id] = 1;
      Object.keys(els).forEach(function (k) { els[k].classList.toggle('is-line', !!line[k]); });
      panel.textContent = '';
      h('div', 'pg-eyebrow', panel, 'checkpoint');
      h('code', 'pg-ckid', panel, c.id);
      var dl = h('dl', 'pg-dl', panel);
      function row(k, v) { h('dt', '', dl, k); var dd = h('dd', '', dl); if (typeof v === 'string') dd.textContent = v; else dd.appendChild(v); }
      row('step', String(c.step)); row('source', c.source || '');
      row('parent', c.parent ? short(c.parent) : 'none');
      row('next', (c.next || []).join(', ') || 'nothing (done)');
      if (c.label) row('made by', c.label);
      if (c.run && D.runs) D.runs.forEach(function (r) { if (r.id === c.run) row('run', r.label); });
      if (c.values) { var pre = h('code', 'pg-pre'); pre.textContent = JSON.stringify(c.values, null, 1); row('values', pre); }
      (c.tasks || []).forEach(function (t) { (t.interrupts || []).forEach(function (v) { row('interrupt', t.name + ': ' + fmt(v, 60)); }); });
      if ((c.pending_writes || []).length) {
        h('div', 'pg-ph', panel, 'pending writes (saved against this checkpoint)');
        var tb = h('table', 'pg-table', panel), b = h('tbody', '', tb);
        c.pending_writes.forEach(function (w) {
          var tr = h('tr', /^__/.test(w[1]) ? 'is-sys' : '', b);
          h('td', 'pg-dim', tr, /^0{8}-/.test(w[0]) ? 'null task' : short(w[0]));
          h('code', '', h('td', '', tr), w[1]);
          h('code', 'pg-val', h('td', '', tr), fmt(w[2], 40));
        });
      }
    }
    pick(by[D.head] || cps[cps.length - 1]);
  }

  // ---- :::interrupt ------------------------------------------------------------------------------------------------------
  function interrupt(fig, D) {
    var lg = head(fig, 'interrupt and resume', D.title);
    key(lg, 'pg-sw-ran', 'ran this time'); key(lg, 'pg-sw-irq', 'interrupt()'); key(lg, 'pg-sw-lost', 'work thrown away');
    var flat = [];
    (D.runs || []).forEach(function (r, ri) { (r.events || []).forEach(function (e, k) { flat.push({ e: e, r: r, ri: ri, k: k }); }); });
    var body = h('div', 'pg-irow', fig);
    var code = h('div', 'pg-code', body);
    h('div', 'pg-ph', code, D.node ? 'node ' + D.node : 'the node');
    var lines = (D.code || []).map(function (t, i) {
      var r = h('div', 'pg-line', code);
      h('span', 'pg-ln', r, String(i + 1));
      h('code', 'pg-lt', r, t);
      r._tag = h('span', 'pg-ltag', r);
      return r;
    });
    var side = h('div', 'pg-iside', body);
    var runH = h('div', 'pg-runh', side);
    var queue = h('div', 'pg-queue', side);
    var log = h('ol', 'pg-log', side);
    function text(e) {
      switch (e.kind) {
        case 'step': return (e.step !== undefined ? 'step ' + e.step + ': ' : '') + (e.node || D.node) + ' runs' + (e.note ? '. ' + e.note : '');
        case 'line': return 'line ' + e.line + (e.note ? ': ' + e.note : '');
        case 'interrupt': return (e.resumed ? 'interrupt #' + e.index + ' returns ' + fmt(e.value, 40) + ' (resume value ' + e.index + ')'
          : 'interrupt #' + e.index + ' raises ' + fmt(e.value, 40) + '; the node stops here') + (e.note ? '. ' + e.note : '');
        case 'resume': return 'Command(resume' + (e.value !== undefined ? '=' + fmt(e.value, 40) : '') + ')' + (e.note ? ': ' + e.note : '');
        case 'write': return 'write ' + (e.channel || '') + (e.value !== undefined ? ' = ' + fmt(e.value, 48) : '') + (e.note ? ': ' + e.note : '');
        case 'discard': return e.note || 'the node’s partial work is thrown away';
        case 'checkpoint': return 'checkpoint ' + short(e.id) + ' saved' + (e.pending ? ', pending ' + e.pending.map(function (p) { return p[1]; }).join(', ') : '') + (e.note ? '. ' + e.note : '');
        case 'return': return e.value !== undefined ? 'the call returns ' + fmt(e.value, 60) + (e.note ? '. ' + e.note : '') : (e.note || 'the call returns');
        default: return e.note || '';
      }
    }
    function show(i) {
      var cur = flat[i], run = cur.r;
      runH.textContent = '';
      h('span', 'pg-eyebrow', runH, 'run ' + (cur.ri + 1) + ' of ' + D.runs.length);
      h('code', 'pg-runlab', runH, run.label || '');
      // the resume values this run brings, and which interrupt has taken each
      queue.textContent = '';
      var rv = run.resume || [];
      if (rv.length) {
        h('span', 'pg-dim', queue, 'resume values, matched by call order: ');
        var used = {};
        for (var j = 0; j <= cur.k; j++) { var e0 = run.events[j]; if (e0.kind === 'interrupt' && e0.resumed) used[e0.index] = 1; }
        rv.forEach(function (v, n) { h('span', 'pg-chip' + (used[n] ? ' is-used' : ''), queue, '#' + n + ' ' + fmt(v, 24)); });
      } else h('span', 'pg-dim', queue, 'no resume values: a fresh call');
      // the code: lines run in this run so far, the current one, and the work lost at an interrupt
      var ran = {}, lost = false, tags = {};
      for (var k = 0; k <= cur.k; k++) {
        var e = run.events[k];
        if (e.line) ran[e.line] = 1;
        if (e.kind === 'interrupt') tags[e.line] = e.resumed ? '#' + e.index + ' → ' + fmt(e.value, 18) : '#' + e.index + ' raised';
        if (e.kind === 'discard') lost = true;
        if (e.kind === 'step') { ran = {}; tags = {}; lost = false; }
      }
      lines.forEach(function (r, n) {
        var ln = n + 1;
        r.classList.toggle('is-ran', !!ran[ln]);
        r.classList.toggle('is-cur', cur.e.line === ln);
        r.classList.toggle('is-lost', lost && !!ran[ln]);
        r.classList.toggle('is-irq', !!tags[ln]);
        r._tag.textContent = tags[ln] || '';
      });
      log.textContent = '';
      run.events.forEach(function (e, k) {
        var li = h('li', 'pg-ev pg-ev-' + e.kind + (k === cur.k ? ' is-cur' : k < cur.k ? ' is-past' : ''), log);
        h('span', 'pg-evk', li, e.kind);
        h('span', 'pg-evt', li, text(e));
      });
    }
    if (paper(fig)) { show(flat.length - 1); return; }
    controls(fig, flat.length, show, function (i) { return 'event ' + (i + 1) + ' of ' + flat.length; }).go(0);
  }

  var VIEWS = { superstep: superstep, fanout: fanout, reducer: reducer, checkpoints: checkpoints, interrupt: interrupt };
  function build(fig) {
    var src = fig.querySelector(':scope > script[type="application/json"]');
    var kind = fig.getAttribute('data-pregel');
    if (!src || !VIEWS[kind]) return;
    fig.classList.add('pg', 'pg-' + kind, 'pg-ready');
    var cap = fig.querySelector(':scope > figcaption');
    try { VIEWS[kind](fig, JSON.parse(src.textContent)); }
    catch (err) { h('pre', 'pg-error', fig, 'pregel ' + kind + ': ' + String(err.message || err)); }
    if (cap) fig.appendChild(cap);
    fig.pregel = true;
  }
  function boot() {
    Array.prototype.forEach.call(document.querySelectorAll('[data-pregel]'), function (f) { if (!f.pregel) build(f); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
  window.pregel = { boot: boot };
})();
