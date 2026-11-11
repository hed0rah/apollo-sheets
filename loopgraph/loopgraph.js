/* loopgraph: an agent loop drawn from data, and a run replayed over it.
   one <figure class="lg" data-loopgraph> per graph, holding a <script type="application/json"> with the graph.
   no dependencies, no eval, no inline handlers; colours come from the page's tokens (loopgraph.css). */
(function () {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg';
  var TAG = { start: 'START', end: 'END', llm: 'MODEL', tool: 'TOOL', router: 'ROUTE', human: 'HUMAN',
              step: 'STEP', store: 'STORE', fail: 'FAIL', group: 'SUBGRAPH' };
  var EDGE_NAME = { next: 'next', cond: 'conditional', loop: 'loop, bounded', fail: 'failure path',
                    resume: 'human answer', send: 'fan-out' };
  var GAP_MAIN = 58, GAP_CROSS = 26, LANE = 24, PAD = 18, GROUP_HEAD = 26, GROUP_PAD = 16;
  var PAPER = false;                            // set while a paper figure is laid out: tighter ranks
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var figN = 0;

  function el(tag, attrs, parent) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) if (attrs[k] !== undefined && attrs[k] !== null) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function h(tag, cls, parent, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }
  function txt(parent, x, y, s, cls, anchor) {
    var t = el('text', { x: x, y: y, 'class': cls, 'text-anchor': anchor || 'start' }, parent);
    t.textContent = s;
    return t;
  }

  // ---- text measure ------------------------------------------------------------------------------------
  var ctx2d = document.createElement('canvas').getContext('2d');
  function fonts(fig) {
    var cs = getComputedStyle(fig);
    return { sans: cs.getPropertyValue('--sans').trim() || 'system-ui, sans-serif',
             mono: cs.getPropertyValue('--mono').trim() || 'ui-monospace, monospace' };
  }
  function tw(s, font) { ctx2d.font = font; return ctx2d.measureText(s || '').width; }

  // ---- the graph: normalise -----------------------------------------------------------------------------
  function normalise(g) {
    g.dir = g.dir === 'TB' ? 'TB' : 'LR';
    g.state = g.state || {};
    g.groups = g.groups || [];
    g.limits = g.limits || {};
    g.run = g.run || [];
    g.byId = {};
    g.nodes.forEach(function (n, i) {
      n.kind = TAG[n.kind] ? n.kind : 'step';
      n.label = n.label || (n.kind === 'start' ? 'start' : n.kind === 'end' ? 'end' : n.id);
      n.order = i;
      g.byId[n.id] = n;
    });
    g.gById = {};
    g.groups.forEach(function (gr) { gr.collapsed = !!gr.collapsed; g.gById[gr.id] = gr; });
    g.edges.forEach(function (e, i) {
      e.i = i;
      e.kind = EDGE_NAME[e.kind] ? e.kind : (e.when ? 'cond' : 'next');
      if (!g.byId[e.from] || !g.byId[e.to]) throw new Error('loopgraph: edge ' + e.from + ' -> ' + e.to + ' names no node');
    });
    // the replay: which edge each step took, the state after it, loop counts
    var state = {}, counts = {}, prev = null;
    Object.keys(g.state).forEach(function (k) { state[k] = initial(g.state[k].reducer); });
    g.steps = g.run.map(function (s, i) {
      if (!g.byId[s.node]) throw new Error('loopgraph: run step ' + i + ' names no node ' + s.node);
      var from = s.via || prev, edge = null;
      if (from) {
        g.edges.forEach(function (e) { if (!edge && e.from === from && e.to === s.node) edge = e; });
      }
      if (edge) counts[edge.i] = (counts[edge.i] || 0) + 1;
      var writes = s.writes || {};
      state = apply(state, writes, g.state);
      prev = s.node;
      return { i: i, node: s.node, edge: edge, writes: writes, state: state, counts: copy(counts),
               note: s.note, t: s.t, pause: s.pause, checkpoint: s.checkpoint };
    });
    // the keys each node writes: declared, and seen in the run
    g.nodes.forEach(function (n) { n.writeSet = {}; (n.writes || []).forEach(function (k) { n.writeSet[k] = 'declared'; }); });
    g.steps.forEach(function (s) {
      Object.keys(s.writes).forEach(function (k) { g.byId[s.node].writeSet[k] = g.byId[s.node].writeSet[k] || 'seen'; });
    });
    return g;
  }
  function initial(r) { return r === 'append' ? [] : r === 'sum' ? 0 : r === 'merge' ? {} : ''; }
  function copy(o) { var r = {}; for (var k in o) r[k] = o[k]; return r; }
  function apply(state, writes, spec) {
    var next = copy(state);
    Object.keys(writes).forEach(function (k) {
      var r = (spec[k] || {}).reducer || 'replace', v = writes[k];
      if (r === 'append') next[k] = (next[k] || []).concat([v]);
      else if (r === 'sum') next[k] = (+next[k] || 0) + (+v || 0);
      else if (r === 'merge') { next[k] = copy(next[k] || {}); for (var j in v) next[k][j] = v[j]; }
      else next[k] = v;
    });
    return next;
  }

  // ---- layout: layered, with back edges lifted into lanes -------------------------------------------------
  // works in (main, cross) space: main runs along the flow (x for LR, y for TB).
  // virtual ids: '~n' a waypoint a long edge takes through a rank; 'in:i' / 'out:i' where edge i crosses a group's border
  var nDummy = 0;
  function virt(id) { return /^(~|in:|out:)/.test(id); }
  function layered(items, edges, size, labelW) {
    var ids = items.slice(), idx = {};
    ids.forEach(function (id, i) { idx[id] = i; });
    var fwd = [], back = [];
    edges.forEach(function (e) { (e.isLoop ? back : fwd).push(e); });
    // break any cycle the declared loops did not: dfs in source order
    var out = {}, seen = {}, onstack = {}, keep = [];
    ids.forEach(function (id) { out[id] = []; });
    fwd.forEach(function (e) { out[e.u].push(e); });
    function dfs(u) {
      seen[u] = onstack[u] = true;
      out[u].forEach(function (e) {
        if (onstack[e.v]) { e.isLoop = true; back.push(e); }
        else { keep.push(e); if (!seen[e.v]) dfs(e.v); }
      });
      onstack[u] = false;
    }
    var indeg = {};
    fwd.forEach(function (e) { indeg[e.v] = (indeg[e.v] || 0) + 1; });
    ids.filter(function (id) { return !indeg[id]; }).concat(ids).forEach(function (id) { if (!seen[id]) dfs(id); });
    fwd = keep;
    // ranks: longest path, then sinks pulled back beside their latest predecessor, border ports outermost
    var rank = {};
    ids.forEach(function (id) { rank[id] = 0; });
    for (var pass = 0; pass <= ids.length; pass++) {
      var moved = false;
      fwd.forEach(function (e) { if (rank[e.v] < rank[e.u] + 1) { rank[e.v] = rank[e.u] + 1; moved = true; } });
      if (!moved) break;
    }
    ids.forEach(function (id) {
      if (virt(id)) return;
      var outs = fwd.filter(function (e) { return e.u === id; }), ins = fwd.filter(function (e) { return e.v === id; });
      if (!outs.length && ins.length) rank[id] = Math.max.apply(null, ins.map(function (e) { return rank[e.u] + 1; }));
    });
    var maxr = 0;
    ids.forEach(function (id) { if (!/^out:/.test(id)) maxr = Math.max(maxr, rank[id]); });
    ids.forEach(function (id) { if (/^out:/.test(id)) rank[id] = maxr + 1; });
    // segments: a long edge becomes a chain through waypoints, one per rank it passes
    var segs = [];
    fwd.forEach(function (e) {
      e.chain = [];
      var prev = e.u;
      for (var r = rank[e.u] + 1; r < rank[e.v]; r++) {
        var d = '~' + (++nDummy);
        ids.push(d); rank[d] = r; idx[d] = ids.length; e.chain.push(d);
        segs.push({ u: prev, v: d }); prev = d;
      }
      segs.push({ u: prev, v: e.v });
    });
    var nr = 0;
    ids.forEach(function (id) { nr = Math.max(nr, rank[id] + 1); });
    var layers = [];
    for (var r0 = 0; r0 < nr; r0++) layers.push([]);
    ids.forEach(function (id) { layers[rank[id]].push(id); });
    var predOf = {}, succOf = {};
    ids.forEach(function (id) { predOf[id] = []; succOf[id] = []; });
    segs.forEach(function (s) { predOf[s.v].push(s.u); succOf[s.u].push(s.v); });
    // order: barycentre sweeps; the ends of back edges lean to the lane side
    var lean = {};
    back.forEach(function (e) { lean[e.u] = 1; lean[e.v] = 1; });
    var pos = {};
    function setPos() { layers.forEach(function (L) { L.forEach(function (id, i) { pos[id] = i; }); }); }
    setPos();
    function bary(L, nb) {
      var b = {};
      L.forEach(function (id) {
        var ns = nb[id];
        b[id] = (ns.length ? ns.reduce(function (a, x) { return a + pos[x]; }, 0) / ns.length : pos[id]) - (lean[id] ? .6 : 0);
      });
      L.sort(function (a, c) { return b[a] - b[c] || idx[a] - idx[c]; });
    }
    for (var sw = 0; sw < 6; sw++) {
      for (var a = 1; a < nr; a++) { bary(layers[a], predOf); setPos(); }
      for (var d2 = nr - 2; d2 >= 0; d2--) { bary(layers[d2], succOf); setPos(); }
    }
    // main axis: ranks side by side; a rank of only waypoints and ports is thin
    var gap = layers.map(function (L) { return L.every(virt) ? (PAPER ? 16 : 26) : (PAPER ? 30 : GAP_MAIN); });
    var chips = layers.map(function () { return 0; });
    if (labelW) fwd.forEach(function (e) {
      var r = rank[e.u], first = e.chain.length ? e.chain[0] : e.v;
      if (e.e && labelW(e.e)) chips[r]++;
      if (rank[first] === r + 1 && e.e && !virt(e.u)) gap[r] = Math.max(gap[r], labelW(e.e) + 30);
    });
    // top to bottom, the chips leaving a rank stack in its gap: room for each of them
    if (labelW && labelW.stack) chips.forEach(function (n, r) { if (n > 1) gap[r] = Math.max(gap[r], 12 + 24 * n); });
    var box = {}, m = 0;
    function sz(id) { return virt(id) ? { ms: 0, cs: /^~/.test(id) ? 12 : 4 } : size(id); }
    layers.forEach(function (L, ri) {
      var w = 0;
      L.forEach(function (id) { w = Math.max(w, sz(id).ms); });
      L.forEach(function (id) { var s = sz(id); box[id] = { m: m + (w - s.ms) / 2, ms: s.ms, cs: s.cs, rank: rank[id] }; });
      m += w + gap[ri];
    });
    // cross axis: two passes, each node toward its neighbours' centre, then no overlaps
    function place(L, nb, ri, dirn) {
      var want = L.map(function (id) {
        var ps = nb[id].filter(function (p) { return dirn > 0 ? rank[p] < ri : rank[p] > ri; });
        if (!ps.length) return NaN;
        return ps.reduce(function (acc, p) { return acc + box[p].c + box[p].cs / 2; }, 0) / ps.length;
      });
      var c = [], acc = 0;
      L.forEach(function (id, i) {
        var half = box[id].cs / 2, gp = virt(id) || (i && virt(L[i - 1])) ? 12 : GAP_CROSS;
        var w = isNaN(want[i]) ? (box[id].c !== undefined ? box[id].c + half : acc + half) : want[i];
        if (i === 0) c.push(w);
        else c.push(Math.max(w, c[i - 1] + box[L[i - 1]].cs / 2 + gp + half));
        acc = c[i] + half + GAP_CROSS;
      });
      var diffs = [];
      L.forEach(function (id, i) { if (!isNaN(want[i])) diffs.push(want[i] - c[i]); });
      var shift = diffs.length ? diffs.reduce(function (x, y) { return x + y; }, 0) / diffs.length : 0;
      L.forEach(function (id, i) { box[id].c = c[i] + shift - box[id].cs / 2; });
    }
    layers.forEach(function (L, ri) { place(L, predOf, ri, 1); });
    for (var rr = nr - 2; rr >= 0; rr--) place(layers[rr], succOf, rr, -1);
    for (var r2 = 1; r2 < nr; r2++) place(layers[r2], predOf, r2, 1);
    var cmin = Infinity;
    ids.forEach(function (id) { cmin = Math.min(cmin, box[id].c); });
    ids.forEach(function (id) { box[id].c -= cmin; });
    // lanes for back edges: outside what they span, nested by span
    function span(e) { return Math.abs(box[e.u].rank - box[e.v].rank); }
    back.sort(function (x, y) { return span(x) - span(y); });
    var placed = [];
    back.forEach(function (e) {
      var lo = Math.min(box[e.u].rank, box[e.v].rank), hi = Math.max(box[e.u].rank, box[e.v].rank), top = Infinity;
      ids.forEach(function (id) { if (box[id].rank >= lo && box[id].rank <= hi) top = Math.min(top, box[id].c); });
      var level = 1;
      placed.forEach(function (p) { if (p.lo <= hi && lo <= p.hi) level = Math.max(level, p.level + 1); });
      e.lane = top - level * LANE; e.level = level; e.chain = [];
      placed.push({ lo: lo, hi: hi, level: level });
    });
    var ext = { m0: 0, m1: 0, c0: 0, c1: 0 };
    ids.forEach(function (id) { var b = box[id]; ext.m1 = Math.max(ext.m1, b.m + b.ms); ext.c1 = Math.max(ext.c1, b.c + b.cs); });
    back.forEach(function (e) { ext.c0 = Math.min(ext.c0, e.lane - 12); });
    return { box: box, edges: fwd.concat(back), ext: ext };
  }

  // the whole figure: an expanded group is laid out first, with a port on its border for every edge that
  // crosses it, and enters the outer layout as one block
  function layout(g, fig) {
    var F = fonts(fig), LR = g.dir === 'LR';
    nDummy = 0;
    function nodeSize(n) {
      if (n.kind === 'start' || n.kind === 'end') return { w: Math.max(56, tw(n.label, '600 12px ' + F.sans) + 30), h: 30 };
      var tag = TAG[n.kind] + (n.tags && n.tags.length ? '   ' + n.tags.join('  ') : '');
      var w = Math.max(tw(n.label, '600 13.5px ' + F.sans), tw(n.sub, '11.5px ' + F.sans), tw(tag, '9.5px ' + F.mono) + 6);
      return { w: Math.max(104, Math.ceil(w) + 34 + (n.kind === 'router' ? 22 : 0)), h: n.sub ? 60 : 48 };
    }
    function labelW(e) {
      var l = e.kind === 'loop' ? '' : chipText(e);
      if (!l) return 0;
      return LR ? tw(l, '10.5px ' + F.mono) + 14 : (PAPER ? 30 : 40);
    }
    function groupNodeSize(gr) {
      var n = g.nodes.filter(function (x) { return x.group === gr.id; }).length;
      return { w: Math.max(130, tw(gr.label, '600 13.5px ' + F.sans) + 44), h: 60, count: n };
    }
    function msz(s) { return LR ? { ms: s.w, cs: s.h } : { ms: s.h, cs: s.w }; }
    labelW.stack = !LR;
    var where = {};                                      // node id -> its top-level item id
    g.nodes.forEach(function (n) { where[n.id] = n.group && g.gById[n.group] ? n.group : n.id; });
    var expanded = {};
    g.groups.forEach(function (gr) { if (!gr.collapsed && g.nodes.some(function (n) { return n.group === gr.id; })) expanded[gr.id] = 1; });
    var inner = {}, outChain = {}, inChain = {};
    Object.keys(expanded).forEach(function (gid) {
      var gr = g.gById[gid];
      var members = g.nodes.filter(function (n) { return n.group === gid; }).map(function (n) { return n.id; });
      var es = [];
      g.edges.forEach(function (e) {
        var a = where[e.from] === gid, b = where[e.to] === gid;
        if (a && b) es.push({ u: e.from, v: e.to, isLoop: e.kind === 'loop', e: e });
        else if (e.kind === 'loop') return;                // a loop crossing the border keeps its lane outside
        else if (a) { members.push('out:' + e.i); es.push({ u: e.from, v: 'out:' + e.i, e: e, port: 'out' }); }
        else if (b) { members.push('in:' + e.i); es.push({ u: 'in:' + e.i, v: e.to, e: e, port: 'in' }); }
      });
      var L = layered(members, es, function (id) { return msz(nodeSize(g.byId[id])); }, labelW);
      var labw = tw(gr.label, '600 11px ' + F.mono) + 60;
      var ms = L.ext.m1 - L.ext.m0 + 2 * GROUP_PAD + (LR ? 0 : GROUP_HEAD), cs = L.ext.c1 - L.ext.c0 + 2 * GROUP_PAD + (LR ? GROUP_HEAD : 0);
      if (LR) ms = Math.max(ms, labw); else cs = Math.max(cs, labw);
      L.edges.forEach(function (x) {
        if (x.port === 'out') outChain[x.e.i] = x.chain.concat(['out:' + x.e.i]);
        if (x.port === 'in') inChain[x.e.i] = ['in:' + x.e.i].concat(x.chain);
      });
      inner[gid] = { L: L, ms: ms, cs: cs };
    });
    var items = [];
    g.nodes.forEach(function (n) { var w = where[n.id]; if (items.indexOf(w) < 0) items.push(w); });
    var top = [];
    g.edges.forEach(function (e) {
      var u = where[e.from], v = where[e.to];
      if (u === v && g.gById[u]) return;                 // inside a group
      top.push({ u: u, v: v, isLoop: e.kind === 'loop', e: e });
    });
    var T = layered(items, top, function (id) {
      if (inner[id]) return { ms: inner[id].ms, cs: inner[id].cs };
      return msz(g.gById[id] ? groupNodeSize(g.gById[id]) : nodeSize(g.byId[id]));
    }, labelW);
    // absolute boxes in (main, cross)
    var abs = {}, groupsOut = [], edgesOut = [];
    Object.keys(T.box).forEach(function (id) {
      var b = T.box[id];
      if (inner[id]) {
        var I = inner[id], hm = LR ? 0 : GROUP_HEAD, hc = LR ? GROUP_HEAD : 0;
        var om0 = b.m + GROUP_PAD + hm - I.L.ext.m0, oc0 = b.c + GROUP_PAD + hc - I.L.ext.c0;
        groupsOut.push({ gr: g.gById[id], b: { m: b.m, c: b.c, ms: b.ms, cs: b.cs } });
        Object.keys(I.L.box).forEach(function (nid) {
          var nb = I.L.box[nid], r = { m: om0 + nb.m, c: oc0 + nb.c, ms: nb.ms, cs: nb.cs };
          // a port sits on the border itself
          if (/^in:/.test(nid)) r.m = b.m;
          if (/^out:/.test(nid)) r.m = b.m + b.ms;
          abs[nid] = r;
        });
        I.L.edges.forEach(function (x) {
          if (x.port) return;
          edgesOut.push({ e: x.e, u: x.u, v: x.v, isLoop: x.isLoop, level: x.level, chain: x.chain, lane: x.isLoop ? x.lane + oc0 : null });
        });
      } else {
        abs[id] = { m: b.m, c: b.c, ms: b.ms, cs: b.cs, groupNode: !!g.gById[id] };
      }
    });
    T.edges.forEach(function (x) {
      // an edge to or from an expanded group's member joins that member through the border port
      var u = inner[x.u] ? x.e.from : x.u, v = inner[x.v] ? x.e.to : x.v;
      var chain = x.isLoop ? [] : (inner[x.u] ? outChain[x.e.i] || [] : []).concat(x.chain, inner[x.v] ? inChain[x.e.i] || [] : []);
      edgesOut.push({ e: x.e, u: u, v: v, isLoop: x.isLoop, level: x.level, chain: chain, lane: x.isLoop ? x.lane : null });
    });
    var ext = { m0: Infinity, m1: -Infinity, c0: Infinity, c1: -Infinity };
    function grow(m, c) { ext.m0 = Math.min(ext.m0, m); ext.m1 = Math.max(ext.m1, m); ext.c0 = Math.min(ext.c0, c); ext.c1 = Math.max(ext.c1, c); }
    Object.keys(abs).forEach(function (id) { var b = abs[id]; grow(b.m, b.c); grow(b.m + b.ms, b.c + b.cs); });
    edgesOut.forEach(function (x) { if (x.lane !== null) grow(ext.m0, x.lane - 14); });
    var om = PAD - ext.m0, oc = PAD + 4 - ext.c0;
    function map(b) { return LR ? { x: b.m + om, y: b.c + oc, w: b.ms, h: b.cs } : { x: b.c + oc, y: b.m + om, w: b.cs, h: b.ms }; }
    var nodes = {}, pts = {};
    Object.keys(abs).forEach(function (id) {
      if (virt(id)) { pts[id] = abs[id]; return; }
      nodes[id] = map(abs[id]); nodes[id].mc = abs[id]; nodes[id].groupNode = abs[id].groupNode;
    });
    var gw = (ext.m1 - ext.m0) + 2 * PAD, gc = (ext.c1 - ext.c0) + 2 * PAD + 8;
    return {
      LR: LR, nodes: nodes, pts: pts, where: where, om: om, oc: oc,
      groups: groupsOut.map(function (x) { var r = map(x.b); r.gr = x.gr; return r; }),
      edges: edgesOut, width: LR ? gw : gc, height: LR ? gc : gw,
      groupNodeSize: groupNodeSize
    };
  }
  function chipText(e) {
    var l = e.when || e.label || '';
    return l.length > 26 ? l.slice(0, 24).replace(/[\s,;:]+$/, '') + '...' : l;
  }

  // ---- edge geometry, in (main, cross) then mapped ----------------------------------------------------------
  function route(Lo, x) {
    var a = Lo.nodes[x.u].mc, b = Lo.nodes[x.v].mc, om = Lo.om, oc = Lo.oc, LR = Lo.LR;
    function P(m, c) { m += om; c += oc; return LR ? [m, c] : [c, m]; }
    function f(p) { return p[0].toFixed(1) + ' ' + p[1].toFixed(1); }
    if (x.isLoop) {
      var lv = (x.level || 1) - 1, sm = a.m + a.ms * Math.min(.9, .66 + .1 * lv), tm = b.m + b.ms * Math.max(.1, .34 - .1 * lv), L = x.lane, r = 9;
      if (x.u === x.v) { sm = a.m + a.ms * 0.72; tm = a.m + a.ms * 0.28; }
      var dir = tm < sm ? -1 : 1;
      var d = 'M' + f(P(sm, a.c)) + ' L' + f(P(sm, L + r)) + ' Q' + f(P(sm, L)) + ' ' + f(P(sm + dir * r, L)) +
              ' L' + f(P(tm - dir * r, L)) + ' Q' + f(P(tm, L)) + ' ' + f(P(tm, L + r)) + ' L' + f(P(tm, b.c - 1));
      return { d: d, mid: P((sm + tm) / 2, L), back: true, lane: [P(sm + dir * r, L), P(tm - dir * r, L)] };
    }
    var p0 = [a.m + a.ms, a.c + a.cs / 2], p3 = [b.m, b.c + b.cs / 2];
    if (p3[0] < p0[0] + 8) {                             // same rank or behind: leave by the cross side
      p0 = [a.m + a.ms / 2, a.c + a.cs]; p3 = [b.m + b.ms / 2, b.c];
      if (p3[1] < p0[1]) { p0 = [a.m + a.ms / 2, a.c]; p3 = [b.m + b.ms / 2, b.c + b.cs]; }
      var k = (p3[1] - p0[1]) / 2, c1 = [p0[0], p0[1] + k], c2 = [p3[0], p3[1] - k];
      return { d: 'M' + f(P(p0[0], p0[1])) + ' C' + f(P(c1[0], c1[1])) + ' ' + f(P(c2[0], c2[1])) + ' ' + f(P(p3[0], p3[1] - 1)),
               mid: P(bz(p0[0], c1[0], c2[0], p3[0], .5), bz(p0[1], c1[1], c2[1], p3[1], .5)) };
    }
    // through the waypoints: one cubic per hop, level at each point, so the edge reads as a single stroke
    var way = [p0];
    (x.chain || []).forEach(function (id) { var q = Lo.pts[id]; if (q) way.push([q.m, q.c + q.cs / 2]); });
    way.push([p3[0] - 1, p3[1]]);
    var dd = 'M' + f(P(way[0][0], way[0][1])), mid = null;
    for (var i = 1; i < way.length; i++) {
      var s = way[i - 1], t = way[i], dm = Math.max(i === 1 || i === way.length - 1 ? 24 : 10, (t[0] - s[0]) * 0.5);
      var q1 = [s[0] + dm, s[1]], q2 = [t[0] - dm, t[1]];
      dd += ' C' + f(P(q1[0], q1[1])) + ' ' + f(P(q2[0], q2[1])) + ' ' + f(P(t[0], t[1]));
      var tt = way.length > 2 ? .72 : .5;
      if (i === 1) mid = P(bz(s[0], q1[0], q2[0], t[0], tt), bz(s[1], q1[1], q2[1], t[1], tt));
    }
    return { d: dd, mid: mid };
  }
  function bz(a, b, c, d, t) { var s = 1 - t; return s * s * s * a + 3 * s * s * t * b + 3 * s * t * t * c + t * t * t * d; }

  // ---- drawing ------------------------------------------------------------------------------------------------
  function draw(F) {
    var g = F.g, id = F.id;
    PAPER = !!F.paper;
    if (F.paper) {
      // on paper the box is a page column: lay it out both ways and keep the one that prints larger
      var best = null;
      ['LR', 'TB'].forEach(function (d) {
        g.dir = d;
        var L = layout(g, F.fig), k = Math.min(F.paper[0] / L.width, F.paper[1] / L.height);
        if (!best || k > best.k) best = { k: k, d: d, L: L };
      });
      g.dir = best.d;
      F.Lo = best.L;
    } else {
      F.Lo = layout(g, F.fig);
    }
    PAPER = false;
    var Lo = F.Lo;
    var svg = F.svg;
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    svg.setAttribute('viewBox', '0 0 ' + Math.ceil(Lo.width) + ' ' + Math.ceil(Lo.height));
    svg.setAttribute('width', Math.ceil(Lo.width));
    svg.setAttribute('height', Math.ceil(Lo.height));
    fit(F);
    var defs = el('defs', {}, svg);
    ['next', 'cond', 'loop', 'fail', 'resume', 'send', 'hot'].forEach(function (k) {
      var mk = el('marker', { id: id + '-mk-' + k, viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 7, markerHeight: 7,
                              orient: 'auto', markerUnits: 'userSpaceOnUse', 'class': 'lg-mk lg-mk-' + k }, defs);
      el('path', { d: 'M0 0 L10 5 L0 10 z' }, mk);
    });
    var gG = el('g', { 'class': 'lg-groups' }, svg), gE = el('g', { 'class': 'lg-edges' }, svg),
        gC = el('g', { 'class': 'lg-chips' }, svg), gH = el('g', { 'class': 'lg-heads' }, svg), gN = el('g', { 'class': 'lg-nodes' }, svg);
    F.gTok = el('g', { 'class': 'lg-tokens' }, svg);
    F.nodeEls = {}; F.edgeEls = []; F.badges = {};
    // groups
    Lo.groups.forEach(function (b) {
      el('rect', { x: b.x, y: b.y, width: b.w, height: b.h, rx: 12, 'class': 'lg-group-box' }, gG);
      // the head draws over the edges, so an edge entering the group passes under its title
      var gg = el('g', { 'class': 'lg-group', tabindex: 0, role: 'button', 'aria-label': 'collapse ' + b.gr.label }, gH);
      el('rect', { x: b.x, y: b.y, width: b.w, height: GROUP_HEAD, rx: 12, 'class': 'lg-group-head' }, gg);
      el('rect', { x: b.x, y: b.y + GROUP_HEAD - 10, width: b.w, height: 10, 'class': 'lg-group-head' }, gg);
      txt(gg, b.x + 12, b.y + 17, 'SUBGRAPH', 'lg-tag');
      txt(gg, b.x + 82, b.y + 17.5, b.gr.label, 'lg-group-label');
      txt(gg, b.x + b.w - 12, b.y + 17.5, '−', 'lg-toggle', 'end');
      gg.addEventListener('click', function () { toggle(F, b.gr.id); });
      key(gg, function () { toggle(F, b.gr.id); });
      hover(F, gg, { group: b.gr });
    });
    // edges; chips wait until every badge is down, then take the first clear spot along their edge
    var taken = [], pending = [], nodesT = [], chipsT = [];
    Object.keys(Lo.nodes).forEach(function (nid) { var b = Lo.nodes[nid]; taken.push({ x: b.x - 4, y: b.y - 4, w: b.w + 8, h: b.h + 8 }); });
    nodesT = taken.slice();
    Lo.edges.forEach(function (x) {
      var r = route(Lo, x), e = x.e, kind = x.isLoop && e.kind === 'next' ? 'loop' : e.kind;
      var ge = el('g', { 'class': 'lg-edge lg-e-' + kind }, gE);
      el('path', { d: r.d, 'class': 'lg-edge-hit' }, ge);
      var p = el('path', { d: r.d, 'class': 'lg-edge-line', 'marker-end': 'url(#' + id + '-mk-' + kind + ')' }, ge);
      var rec = { x: x, e: e, g: ge, path: p, kind: kind };
      F.edgeEls.push(rec);
      var label = chipText(e);
      if (kind === 'loop') {
        var text = (e.counter ? e.counter + ' ' : '') + (e.max ? '0/' + e.max : 'loop');
        var w = tw(text + (label ? '  ' + label : ''), '600 10.5px ' + fonts(F.fig).mono) + 30;
        if (r.lane) {                                    // slide along the lane to the first spot clear of boxes
          var la = r.lane[0], lb = r.lane[1];
          [.5, .32, .68, .18, .82].some(function (t) {
            var q = [la[0] + (lb[0] - la[0]) * t, la[1] + (lb[1] - la[1]) * t];
            if (!overlaps({ x: q[0] - w / 2 - 3, y: q[1] - 13, w: w + 6, h: 26 }, taken)) { r.mid = q; return true; }
            return false;
          });
        }
        var bg = el('g', { 'class': 'lg-badge', transform: 'translate(' + r.mid[0].toFixed(1) + ' ' + r.mid[1].toFixed(1) + ')' }, gC);
        el('rect', { x: -w / 2, y: -10, width: w, height: 20, rx: 10, 'class': 'lg-badge-bg' }, bg);
        el('path', { d: 'M' + (-w / 2 + 15.5) + ' -3.2 A4.5 4.5 0 1 0 ' + (-w / 2 + 16.5) + ' 2.8', 'class': 'lg-badge-glyph' }, bg);
        el('path', { d: 'M' + (-w / 2 + 14.2) + ' -6.2 L' + (-w / 2 + 16.4) + ' -2.6 L' + (-w / 2 + 12.4) + ' -2.2 z', 'class': 'lg-badge-head' }, bg);
        var bt = txt(bg, -w / 2 + 24, 3.8, text, 'lg-badge-text');
        if (label) txt(bg, w / 2 - 10, 3.8, label, 'lg-badge-when', 'end');
        rec.badge = { g: bg, t: bt, max: e.max, counter: e.counter };
        taken.push({ x: r.mid[0] - w / 2, y: r.mid[1] - 10, w: w, h: 20 });
        chipsT.push(taken[taken.length - 1]);
      } else if (label) {
        pending.push({ rec: rec, label: label, kind: kind, mid: r.mid, cw: tw(label, '10.5px ' + fonts(F.fig).mono) + 14 });
      }
      hover(F, ge, { edge: e, kind: kind });
    });
    pending.forEach(function (c) {
      var len = c.rec.path.getTotalLength(), at = c.mid, fr = [.5, .4, .6, .3, .7, .22, .78, .15, .85];
      function box(px, py, cw) { return { x: px - cw / 2 - 3, y: py - 12, w: cw + 6, h: 24 }; }
      function cost(b) { return overlaps(b, nodesT, true) + 3 * overlaps(b, chipsT, true); }   // over words is worst
      function search(cw) {
        var best = null, hitAt = null;
        // along the edge, then pushed off the line to either side, a chip's height at a time
        [0, 1, -1, 2, -2, 3, -3, 4, -4].some(function (off) {
          return fr.some(function (f) {
            var q = c.rec.path.getPointAtLength(len * f), q2 = c.rec.path.getPointAtLength(Math.min(len, len * f + 2));
            var tx = q2.x - q.x, ty = q2.y - q.y, n = Math.hypot(tx, ty) || 1;
            var px = q.x - ty / n * off * 20, py = q.y + tx / n * off * 20, o = cost(box(px, py, cw));
            if (!o) { hitAt = [px, py]; return true; }
            if (!best || o < best.o) best = { o: o, at: [px, py] };
            return false;
          });
        });
        return hitAt ? { at: hitAt, clear: true } : { at: best.at, clear: false, o: best.o };
      }
      if (len && cost(box(at[0], at[1], c.cw))) {
        var r1 = search(c.cw);
        if (!r1.clear && c.label.length > 16) {          // nothing clear: a shorter label, the full one in the card
          var short = c.label.slice(0, 13).replace(/[\s,;:]+$/, '') + '...', sw = tw(short, '10.5px ' + fonts(F.fig).mono) + 14;
          var r2 = search(sw);
          if (r2.clear || r2.o < r1.o) { c.label = short; c.cw = sw; r1 = r2; }
        }
        at = r1.at;
      }
      taken.push({ x: at[0] - c.cw / 2, y: at[1] - 9, w: c.cw, h: 18 });
      chipsT.push(taken[taken.length - 1]);
      var cg = el('g', { 'class': 'lg-chip lg-chip-' + c.kind, transform: 'translate(' + at[0].toFixed(1) + ' ' + at[1].toFixed(1) + ')' }, gC);
      el('rect', { x: -c.cw / 2, y: -9, width: c.cw, height: 18, rx: c.kind === 'cond' ? 4 : 9, 'class': 'lg-chip-bg' }, cg);
      txt(cg, 0, 3.6, c.label, 'lg-chip-text', 'middle');
      c.rec.chip = cg;
    });
    // nodes
    Object.keys(Lo.nodes).forEach(function (nid) {
      var b = Lo.nodes[nid];
      if (b.groupNode) drawGroupNode(F, gN, g.gById[nid], b);
      else drawNode(F, gN, g.byId[nid], b);
    });
    legend(F);
    // the drawing's own extent, badges and chips included, so nothing at the edge is clipped
    try {
      var bb = svg.getBBox();
      if (bb.width > 0 && bb.height > 0) {
        var x0 = Math.min(0, bb.x - 6), y0 = Math.min(0, bb.y - 6);
        var w = Math.max(Lo.width, bb.x + bb.width + 6) - x0, hh = Math.max(Lo.height, bb.y + bb.height + 6) - y0;
        svg.setAttribute('viewBox', x0.toFixed(1) + ' ' + y0.toFixed(1) + ' ' + Math.ceil(w) + ' ' + Math.ceil(hh));
        svg.setAttribute('width', Math.ceil(w));
        svg.setAttribute('height', Math.ceil(hh));
        Lo.width = w; Lo.height = hh;
        fit(F);
      }
    } catch (e) { /* not rendered yet: the computed extent stands */ }
  }

  function overlaps(a, list, area) {
    var sum = 0;
    for (var i = 0; i < list.length; i++) {
      var t = list[i], ox = Math.min(a.x + a.w, t.x + t.w) - Math.max(a.x, t.x), oy = Math.min(a.y + a.h, t.y + t.h) - Math.max(a.y, t.y);
      if (ox > 0 && oy > 0) { if (!area) return true; sum += ox * oy; }
    }
    return area ? sum : false;
  }

  function fit(F) {
    var room = F.canvas.clientWidth - 20, w = F.Lo.width, k = room > 0 && w > room ? Math.max(.66, room / w) : 1;
    F.scale = k;
    F.svg.style.width = (w * k).toFixed(0) + 'px';
    F.svg.style.height = (F.Lo.height * k).toFixed(0) + 'px';
  }

  function drawNode(F, parent, n, b) {
    var gn = el('g', { 'class': 'lg-node lg-k-' + n.kind, transform: 'translate(' + b.x + ' ' + b.y + ')', tabindex: 0,
                       role: 'button', 'aria-label': TAG[n.kind] + ' ' + n.label }, parent);
    var w = b.w, hh = b.h;
    el('rect', { x: -5, y: -5, width: w + 10, height: hh + 10, rx: n.kind === 'start' || n.kind === 'end' ? (hh + 10) / 2 : 12, 'class': 'lg-halo' }, gn);
    if (n.kind === 'start' || n.kind === 'end') {
      el('rect', { width: w, height: hh, rx: hh / 2, 'class': 'lg-body' }, gn);
      if (n.kind === 'end') el('rect', { x: 3, y: 3, width: w - 6, height: hh - 6, rx: (hh - 6) / 2, 'class': 'lg-inner' }, gn);
      else el('circle', { cx: 14, cy: hh / 2, r: 3.5, 'class': 'lg-dot' }, gn);
      txt(gn, w / 2 + (n.kind === 'start' ? 5 : 0), hh / 2 + 4.2, n.label, 'lg-term', 'middle');
    } else {
      var shape;
      if (n.kind === 'router') {
        var k = 11;
        shape = el('path', { d: 'M' + k + ' 0 H' + (w - k) + ' L' + w + ' ' + hh / 2 + ' L' + (w - k) + ' ' + hh + ' H' + k + ' L0 ' + hh / 2 + ' z', 'class': 'lg-body' }, gn);
      } else if (n.kind === 'store') {
        shape = el('path', { d: 'M0 7 Q0 0 ' + w / 2 + ' 0 Q' + w + ' 0 ' + w + ' 7 V' + (hh - 7) + ' Q' + w + ' ' + hh + ' ' + w / 2 + ' ' + hh +
                             ' Q0 ' + hh + ' 0 ' + (hh - 7) + ' z', 'class': 'lg-body' }, gn);
        el('path', { d: 'M0 7 Q0 14 ' + w / 2 + ' 14 Q' + w + ' 14 ' + w + ' 7', 'class': 'lg-rim' }, gn);
      } else {
        shape = el('rect', { width: w, height: hh, rx: 7, 'class': 'lg-body' }, gn);
        if (n.kind === 'human') el('rect', { x: 3, y: 3, width: w - 6, height: hh - 6, rx: 5, 'class': 'lg-inner' }, gn);
      }
      var x0 = n.kind === 'router' ? 20 : 14, y0 = n.kind === 'store' ? 6 : 0;
      if (n.kind !== 'router' && n.kind !== 'store') el('rect', { x: 0, y: 0, width: 4, height: hh, rx: 2, 'class': 'lg-stripe' }, gn);
      txt(gn, x0, y0 + 16, TAG[n.kind], 'lg-tag');
      if (n.tags && n.tags.length) txt(gn, w - (n.kind === 'router' ? 18 : 10), y0 + 16, n.tags.join('  '), 'lg-tags', 'end');
      txt(gn, x0, y0 + 33, n.label, 'lg-label');
      if (n.sub) txt(gn, x0, y0 + 49, n.sub, 'lg-sub');
      if (n.kind === 'fail') { el('path', { d: 'M' + (w - 17) + ' 8 l8 8 m0 -8 l-8 8', 'class': 'lg-x' }, gn); }
      if (n.interrupt) {
        var LR = F.Lo.LR, before = n.interrupt !== 'after';
        var ix = LR ? (before ? 0 : w) : w / 2, iy = LR ? hh / 2 : (before ? 0 : hh);
        var ig = el('g', { 'class': 'lg-interrupt', transform: 'translate(' + ix + ' ' + iy + ')' }, gn);
        el('circle', { r: 8 }, ig);
        el('path', { d: 'M-2.4 -3.6 V3.6 M2.4 -3.6 V3.6' }, ig);
      }
    }
    var ck = el('path', { d: 'M' + (w - 2) + ' ' + (hh - 7) + ' l5 5 l-5 5 l-5 -5 z', 'class': 'lg-ckpt' }, gn);
    F.nodeEls[n.id] = { g: gn, n: n, ck: ck };
    gn.addEventListener('click', function () { seekNode(F, n.id); });
    key(gn, function () { seekNode(F, n.id); });
    hover(F, gn, { node: n });
  }

  function drawGroupNode(F, parent, gr, b) {
    var gn = el('g', { 'class': 'lg-node lg-k-group', transform: 'translate(' + b.x + ' ' + b.y + ')', tabindex: 0,
                       role: 'button', 'aria-label': 'expand ' + gr.label }, parent);
    var w = b.w, hh = b.h, n = F.Lo.groupNodeSize(gr).count;
    el('rect', { x: -5, y: -5, width: w + 10, height: hh + 10, rx: 12, 'class': 'lg-halo' }, gn);
    el('rect', { x: 6, y: -6, width: w - 12, height: hh, rx: 7, 'class': 'lg-stack' }, gn);
    el('rect', { x: 3, y: -3, width: w - 6, height: hh, rx: 7, 'class': 'lg-stack' }, gn);
    el('rect', { width: w, height: hh, rx: 7, 'class': 'lg-body' }, gn);
    el('rect', { x: 0, y: 0, width: 4, height: hh, rx: 2, 'class': 'lg-stripe' }, gn);
    txt(gn, 14, 16, 'SUBGRAPH', 'lg-tag');
    txt(gn, w - 12, 16, '+', 'lg-toggle', 'end');
    txt(gn, 14, 33, gr.label, 'lg-label');
    txt(gn, 14, 49, n + ' nodes, collapsed', 'lg-sub');
    var ck = el('path', { d: 'M' + (w - 2) + ' ' + (hh - 7) + ' l5 5 l-5 5 l-5 -5 z', 'class': 'lg-ckpt' }, gn);
    F.nodeEls[gr.id] = { g: gn, group: gr, ck: ck };
    gn.addEventListener('click', function () { toggle(F, gr.id); });
    key(gn, function () { toggle(F, gr.id); });
    hover(F, gn, { group: gr });
  }

  function key(node, fn) {
    node.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); fn(); } });
  }

  function legend(F) {
    var L = F.legend, g = F.g;
    while (L.firstChild) L.removeChild(L.firstChild);
    var kinds = {}, ek = {};
    g.nodes.forEach(function (n) { kinds[n.kind] = 1; if (n.interrupt) kinds.interrupt = 1; });
    if (g.groups.length) kinds.group = 1;
    g.edges.forEach(function (e) { ek[e.kind] = 1; });
    F.Lo.edges.forEach(function (x) { if (x.isLoop) ek.loop = 1; });
    if (g.steps.some(function (s) { return s.checkpoint; })) kinds.checkpoint = 1;
    var order = ['llm', 'tool', 'router', 'step', 'store', 'human', 'fail', 'group'];
    order.forEach(function (k) {
      if (!kinds[k]) return;
      var it = h('span', 'lg-li lg-k-' + k, L);
      h('i', 'lg-sw-node', it); it.appendChild(document.createTextNode(TAG[k].toLowerCase()));
    });
    ['cond', 'loop', 'fail', 'resume', 'send'].forEach(function (k) {
      if (!ek[k]) return;
      var it = h('span', 'lg-li lg-e-' + k, L);
      var s = el('svg', { width: 26, height: 10, 'class': 'lg-sw-edge' }, it);
      el('path', { d: 'M1 5 H25', 'class': 'lg-edge-line' }, s);
      it.appendChild(document.createTextNode(EDGE_NAME[k]));
    });
    if (kinds.interrupt) { var ii = h('span', 'lg-li lg-li-int', L); h('i', 'lg-sw-int', ii); ii.appendChild(document.createTextNode('interrupt')); }
    if (kinds.checkpoint) { var ci = h('span', 'lg-li lg-li-ck', L); h('i', 'lg-sw-ck', ci); ci.appendChild(document.createTextNode('checkpoint')); }
  }

  // ---- hover card ------------------------------------------------------------------------------------------
  function hover(F, node, what) {
    node.addEventListener('mouseenter', function () { card(F, what, node); });
    node.addEventListener('focus', function () { card(F, what, node); });
    node.addEventListener('mouseleave', function () { F.card.hidden = true; });
    node.addEventListener('blur', function () { F.card.hidden = true; });
  }
  function card(F, w, node) {
    var C = F.card;
    while (C.firstChild) C.removeChild(C.firstChild);
    if (w.node) {
      var n = w.node;
      h('div', 'lg-card-k lg-k-' + n.kind, C, TAG[n.kind] + (n.interrupt ? '  /  interrupt ' + (n.interrupt === 'after' ? 'after' : 'before') : ''));
      h('div', 'lg-card-t', C, n.label);
      if (n.doc) h('p', '', C, n.doc);
      row(C, 'reads', n.reads);
      row(C, 'writes', Object.keys(n.writeSet));
      row(C, 'tags', n.tags);
      var ran = F.g.steps.filter(function (s) { return s.node === n.id; }).length;
      if (F.g.steps.length) h('div', 'lg-card-foot', C, ran ? 'runs ' + ran + 'x in this replay; click to step to the next' : 'not reached in this replay');
    } else if (w.group) {
      h('div', 'lg-card-k lg-k-group', C, 'SUBGRAPH');
      h('div', 'lg-card-t', C, w.group.label);
      if (w.group.doc) h('p', '', C, w.group.doc);
      h('div', 'lg-card-foot', C, 'click to ' + (w.group.collapsed ? 'expand' : 'collapse'));
    } else if (w.edge) {
      var e = w.edge;
      h('div', 'lg-card-k lg-e-' + w.kind, C, EDGE_NAME[w.kind]);
      h('div', 'lg-card-t', C, label(F, e.from) + '  →  ' + label(F, e.to));
      if (e.when) row(C, 'when', [e.when]);
      if (e.max) row(C, 'bound', [(e.counter || 'count') + ' <= ' + e.max]);
      if (e.label && !e.when) h('p', '', C, e.label);
      if (e.doc) h('p', '', C, e.doc);
    }
    C.hidden = false;
    var fr = F.canvas.getBoundingClientRect(), nr = node.getBoundingClientRect();
    var x = nr.left - fr.left + F.canvas.scrollLeft, y = nr.bottom - fr.top + F.canvas.scrollTop + 8;
    C.style.left = Math.max(4, Math.min(x, F.canvas.scrollWidth - C.offsetWidth - 4)) + 'px';
    C.style.top = y + 'px';
  }
  function row(C, k, vals) {
    if (!vals || !vals.length) return;
    var r = h('div', 'lg-card-row', C);
    h('span', 'lg-card-rk', r, k);
    vals.forEach(function (v) { h('code', '', r, v); });
  }
  function label(F, id) { return (F.g.byId[id] || {}).label || id; }

  // ---- replay -----------------------------------------------------------------------------------------------
  function toggle(F, gid) {
    var gr = F.g.gById[gid];
    gr.collapsed = !gr.collapsed;
    F.card.hidden = true;
    draw(F);
    show(F, F.at, true);
  }
  function seekNode(F, nid) {
    var s = F.g.steps, n = s.length;
    if (!n) return;
    for (var k = 1; k <= n; k++) {
      var j = (F.at - 1 + k) % n;
      if (s[j].node === nid) { stop(F); show(F, j + 1); return; }
    }
  }
  function counter(F, name, s, edgeI) {
    if (!s) return 0;
    var dot = name ? name.indexOf('.') : -1;
    if (dot > 0 && F.g.state[name.slice(0, dot)]) {       // a field of an object key: spent.llm_calls
      var o = s.state[name.slice(0, dot)];
      return o && typeof o === 'object' ? +o[name.slice(dot + 1)] || 0 : 0;
    }
    var st = name && F.g.state[name];
    if (st && st.reducer === 'sum') return +s.state[name] || 0;
    if (st && st.reducer === 'append') return (s.state[name] || []).length;
    if (st && typeof s.state[name] === 'number') return s.state[name];
    if (edgeI !== undefined) return s.counts[edgeI] || 0;
    var v = 0;
    F.g.edges.forEach(function (e) { if (e.counter === name) v += s.counts[e.i] || 0; });
    return v;
  }
  function vis(F, nid) { return F.Lo.nodes[nid] ? nid : F.Lo.where[nid]; }

  // at = 0 is the graph at rest; at = i shows the state after step i-1 of the run
  function show(F, at, quiet) {
    var g = F.g, steps = g.steps, n = steps.length;
    at = Math.max(0, Math.min(n, at));
    var moved = at === F.at + 1;
    F.at = at;
    F.fig.classList.toggle('lg-running', at > 0);
    if (F.scrub) F.scrub.value = at;
    var cur = at ? steps[at - 1] : null, visited = {}, trav = {}, ck = {};
    for (var i = 0; i < at; i++) {
      visited[vis(F, steps[i].node)] = 1;
      if (steps[i].edge) trav[steps[i].edge.i] = 1;
      if (steps[i].checkpoint) ck[vis(F, steps[i].node)] = 1;
    }
    Object.keys(F.nodeEls).forEach(function (k) {
      var r = F.nodeEls[k];
      r.g.classList.toggle('is-on', !!visited[k]);
      r.g.classList.toggle('is-cur', !!cur && vis(F, cur.node) === k);
      r.g.classList.toggle('has-ck', !!ck[k]);
    });
    F.edgeEls.forEach(function (r) {
      r.g.classList.toggle('is-on', !!trav[r.e.i]);
      var isCur = !!cur && cur.edge && cur.edge.i === r.e.i;
      r.g.classList.toggle('is-cur', isCur);
      r.path.setAttribute('marker-end', 'url(#' + F.id + '-mk-' + (isCur ? 'hot' : r.kind) + ')');
      if (r.badge) {
        var c = r.badge.counter && F.g.state[r.badge.counter] ? counter(F, r.badge.counter, cur) : (cur ? (cur.counts[r.e.i] || 0) : 0);
        r.badge.t.textContent = (r.badge.counter ? r.badge.counter + ' ' : '') + (r.badge.max ? c + '/' + r.badge.max : (at ? c + 'x' : 'loop'));
        r.badge.g.classList.toggle('is-hot', isCur);
        r.badge.g.classList.toggle('is-near', !!r.badge.max && c === r.badge.max - 1);
        r.badge.g.classList.toggle('is-max', !!r.badge.max && c >= r.badge.max);
      }
    });
    if (moved && cur && cur.edge && !quiet) token(F, cur);
    panel(F, cur, at);
    chart(F, at);
  }
  function token(F, s) {
    if (reduce) return;
    var r = F.edgeEls.filter(function (x) { return x.e.i === s.edge.i; })[0];
    if (!r) return;
    var p = r.path, len = p.getTotalLength(), dot = el('circle', { r: 5, 'class': 'lg-token lg-k-' + F.g.byId[s.node].kind }, F.gTok);
    var t0 = null, dur = Math.min(700, 260 + len * 1.1);
    function frame(ts) {
      if (t0 === null) t0 = ts;
      var k = Math.min(1, (ts - t0) / dur), e = k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      var pt = p.getPointAtLength(e * len);
      dot.setAttribute('cx', pt.x); dot.setAttribute('cy', pt.y);
      if (k < 1) requestAnimationFrame(frame); else dot.parentNode && dot.parentNode.removeChild(dot);
    }
    requestAnimationFrame(frame);
  }

  function play(F) {
    if (F.timer) { stop(F); return; }
    if (F.at >= F.g.steps.length) show(F, 0);
    F.playBtn.classList.add('is-on'); F.playBtn.setAttribute('aria-label', 'pause'); F.playBtn.textContent = 'pause';
    function tick() {
      var s = F.g.steps[F.at - 1];
      if (F.at && s && s.pause && !F.resumed) { stop(F); return; }
      F.resumed = false;
      if (F.at >= F.g.steps.length) { stop(F); return; }
      show(F, F.at + 1);
      F.timer = setTimeout(tick, reduce ? 1100 : 900);
    }
    F.timer = setTimeout(tick, 60);
  }
  function stop(F) {
    clearTimeout(F.timer); F.timer = null;
    if (F.playBtn) { F.playBtn.classList.remove('is-on'); F.playBtn.setAttribute('aria-label', 'play'); F.playBtn.textContent = 'play'; }
  }

  // ---- the panel: step, state, writes, checkpoints, limits ------------------------------------------------------
  function panel(F, s, at) {
    var g = F.g, n = g.steps.length, P = F.stepBox;
    while (P.firstChild) P.removeChild(P.firstChild);
    var head = h('div', 'lg-step-head', P);
    h('span', 'lg-step-n', head, at ? 'step ' + at + ' / ' + n : 'at rest');
    if (s && s.t) h('span', 'lg-step-t', head, s.t);
    if (s) {
      var nn = g.byId[s.node];
      var who = h('div', 'lg-step-who lg-k-' + nn.kind, P);
      h('span', 'lg-step-k', who, TAG[nn.kind]);
      h('span', '', who, nn.label);
      if (s.edge && (s.edge.when || s.edge.label)) h('div', 'lg-step-via', P, 'via ' + (s.edge.when || s.edge.label));
      if (s.note) h('p', 'lg-step-note', P, s.note);
      if (s.pause) {
        var pb = h('div', 'lg-pause', P);
        h('span', 'lg-pause-k', pb, 'interrupt');
        h('span', '', pb, s.pause);
        if (at < n) {
          var b = h('button', 'lg-btn lg-resume', pb, 'resume');
          b.type = 'button';
          b.addEventListener('click', function () { F.resumed = true; if (!F.timer) play(F); });
        }
      }
    } else {
      h('p', 'lg-step-note', P, n ? 'The graph at rest. Play the run, drag the scrubber, or click a node to step to where it runs.' : 'No run recorded for this graph.');
    }
    // limits
    var LB = F.limits;
    while (LB.firstChild) LB.removeChild(LB.firstChild);
    Object.keys(g.limits).forEach(function (k) {
      // a limit is a number or {max, of}: "of" names the state key or loop counter it bounds.
      // recursion_limit counts super-steps; a limit that bounds nothing in the run is a fixed setting
      var L = g.limits[k], max = +(typeof L === 'object' ? L.max : L), of = typeof L === 'object' && L.of ? L.of : k, v;
      if (g.state[of] || g.state[of.split('.')[0]] || g.edges.some(function (e) { return e.counter === of; })) v = counter(F, of, s);
      else if (/^(recursion_limit|super_?steps)$/.test(k)) v = at;
      else { var fx = h('div', 'lg-meter lg-fixed', LB); h('span', 'lg-meter-k', fx, k); h('span', 'lg-meter-bar', fx); h('span', 'lg-meter-v', fx, String(max)); return; }
      var m = h('div', 'lg-meter' + (v >= max ? ' is-max' : v >= max * 0.8 ? ' is-near' : ''), LB);
      h('span', 'lg-meter-k', m, k);
      var bar = h('span', 'lg-meter-bar', m);
      h('i', '', bar).style.width = Math.min(100, 100 * v / max) + '%';
      h('span', 'lg-meter-v', m, v + ' / ' + max);
    });
    // state
    var SB = F.stateBox, keys = Object.keys(g.state);
    while (SB.firstChild) SB.removeChild(SB.firstChild);
    if (!keys.length) h('p', 'lg-empty', SB, 'No typed state declared.');
    keys.forEach(function (k) {
      var spec = g.state[k], v = s ? s.state[k] : initial(spec.reducer), wrote = s && k in s.writes;
      var r = h('div', 'lg-key' + (wrote ? ' is-w' : ''), SB);
      var top = h('div', 'lg-key-top', r);
      h('code', 'lg-key-n', top, k);
      h('span', 'lg-red lg-red-' + (spec.reducer || 'replace'), top, spec.reducer || 'replace');
      if (wrote) h('span', 'lg-key-mark', top, spec.reducer === 'append' ? '+1' : spec.reducer === 'sum' ? '+' + s.writes[k] : 'set');
      var val = h('div', 'lg-key-v', r);
      if (spec.reducer === 'append') {
        var list = v || [];
        if (!list.length) h('span', 'lg-nil', val, 'empty');
        list.slice(-3).forEach(function (item, j) {
          h('div', 'lg-item' + (wrote && j === Math.min(3, list.length) - 1 ? ' is-new' : ''), val, fmt(item));
        });
        if (list.length > 3) h('div', 'lg-more', val, list.length + ' items, last 3 shown');
      } else if (spec.reducer === 'merge') {
        var ks = Object.keys(v || {});
        if (!ks.length) h('span', 'lg-nil', val, 'empty');
        ks.forEach(function (j) { var it = h('div', 'lg-item' + (wrote && j in s.writes[k] ? ' is-new' : ''), val); h('b', '', it, j + ' '); it.appendChild(document.createTextNode(fmt(v[j]))); });
      } else {
        var sv = fmt(v);
        if (sv === '') h('span', 'lg-nil', val, 'unset'); else h('span', '', val, sv);
      }
      r.title = spec.doc || '';
    });
    // writes matrix: node x key
    var WB = F.writesBox;
    while (WB.firstChild) WB.removeChild(WB.firstChild);
    var writers = g.nodes.filter(function (x) { return Object.keys(x.writeSet).length; });
    if (!writers.length || !keys.length) h('p', 'lg-empty', WB, 'No node declares writes.');
    else {
      var tb = h('table', 'lg-wm', WB), tr = h('tr', '', h('thead', '', tb));
      h('th', '', tr, '');
      keys.forEach(function (k) { var th = h('th', '', tr); h('span', '', th, k); });
      var body = h('tbody', '', tb);
      writers.forEach(function (x) {
        var row = h('tr', s && s.node === x.id ? 'is-cur' : '', body);
        var th = h('th', 'lg-k-' + x.kind, row); h('i', 'lg-sw-node', th); th.appendChild(document.createTextNode(x.label));
        keys.forEach(function (k) {
          var td = h('td', '', row), m = x.writeSet[k];
          if (m) { var dot = h('i', 'lg-wd lg-wd-' + m, td); dot.title = x.label + ' writes ' + k + (m === 'seen' ? ' (seen in the run, not declared)' : ''); }
          if (s && s.node === x.id && k in s.writes) td.className = 'is-w';
        });
      });
      h('p', 'lg-wm-foot', WB, 'filled: declared; ring: seen in the run only; lit: written at this step');
    }
    // checkpoints
    var CB = F.ckBox;
    while (CB.firstChild) CB.removeChild(CB.firstChild);
    var cks = g.steps.filter(function (x) { return x.checkpoint; });
    if (!cks.length) h('p', 'lg-empty', CB, 'No checkpoints in this run.');
    cks.forEach(function (x) {
      var b = h('button', 'lg-ck' + (x.i < at ? ' is-on' : '') + (x.i === at - 1 ? ' is-cur' : ''), CB);
      b.type = 'button';
      h('code', '', b, x.checkpoint);
      h('span', '', b, 'step ' + (x.i + 1) + '  ' + label(F, x.node));
      if (x.pause) h('span', 'lg-ck-int', b, 'interrupt');
      b.addEventListener('click', function () { stop(F); show(F, x.i + 1); });
    });
    if (cks.length) h('p', 'lg-wm-foot', CB, 'click one to travel back to it: the state shown is what a resume from there would load');
  }
  function fmt(v) {
    if (v === null || v === undefined) return '';
    if (typeof v === 'object') return JSON.stringify(v);
    return String(v);
  }

  // ---- the run chart: node by step ---------------------------------------------------------------------------
  function chart(F, at) {
    var g = F.g, steps = g.steps, C = F.chartSvg;
    if (!steps.length) { F.chartWrap.hidden = true; return; }
    var rows = [];
    steps.forEach(function (s) { var v = vis(F, s.node); if (rows.indexOf(v) < 0) rows.push(v); });
    // order rows as the layout reads: main axis first
    rows.sort(function (a, b) {
      var A = F.Lo.nodes[a].mc, B = F.Lo.nodes[b].mc;
      return (A.m - B.m) || (A.c - B.c);
    });
    var fnt = fonts(F.fig), lw = 0;
    rows.forEach(function (r) { lw = Math.max(lw, tw(rlabel(F, r), '11.5px ' + fnt.sans)); });
    lw = Math.ceil(lw) + 22;
    var cw = 26, rh = 20, top = 22, W = lw + steps.length * cw + 12, H = top + rows.length * rh + 8;
    while (C.firstChild) C.removeChild(C.firstChild);
    C.setAttribute('viewBox', '0 0 ' + W + ' ' + H); C.setAttribute('width', W); C.setAttribute('height', H);
    rows.forEach(function (r, i) {
      var y = top + i * rh;
      el('rect', { x: 0, y: y, width: W, height: rh, 'class': 'lg-ch-row' + (i % 2 ? ' odd' : '') }, C);
      var kk = F.g.gById[r] ? 'group' : F.g.byId[r].kind;
      el('rect', { x: 6, y: y + 6, width: 8, height: 8, rx: 2, 'class': 'lg-ch-sw lg-k-' + kk }, C);
      txt(C, 20, y + 14, rlabel(F, r), 'lg-ch-label');
    });
    if (at) el('rect', { x: lw + (at - 1) * cw, y: 2, width: cw, height: H - 4, rx: 4, 'class': 'lg-ch-cur' }, C);
    var pts = steps.map(function (s, i) { return [lw + i * cw + cw / 2, top + rows.indexOf(vis(F, s.node)) * rh + rh / 2]; });
    var dAll = 'M' + pts.map(function (p) { return p.join(' '); }).join(' L');
    el('path', { d: dAll, 'class': 'lg-ch-path' }, C);
    if (at > 1) el('path', { d: 'M' + pts.slice(0, at).map(function (p) { return p.join(' '); }).join(' L'), 'class': 'lg-ch-path is-on' }, C);
    steps.forEach(function (s, i) {
      var p = pts[i], kk = F.g.gById[vis(F, s.node)] ? 'group' : g.byId[s.node].kind;
      var gg = el('g', { 'class': 'lg-ch-step lg-k-' + kk + (i < at ? ' is-on' : '') + (i === at - 1 ? ' is-cur' : ''), tabindex: -1 }, C);
      el('rect', { x: p[0] - cw / 2, y: 0, width: cw, height: H, 'class': 'lg-ch-hit' }, gg);
      if (s.edge && (s.edge.kind === 'loop' || F.edgeEls.some(function (r) { return r.e.i === s.edge.i && r.kind === 'loop'; })))
        el('circle', { cx: p[0], cy: p[1], r: 8, 'class': 'lg-ch-loop' }, gg);
      el('circle', { cx: p[0], cy: p[1], r: 4.5, 'class': 'lg-ch-dot' }, gg);
      txt(gg, p[0], 13, String(i + 1), 'lg-ch-n', 'middle');
      if (s.checkpoint) el('path', { d: 'M' + p[0] + ' ' + (p[1] - 13) + ' l3.5 3.5 l-3.5 3.5 l-3.5 -3.5 z', 'class': 'lg-ch-ck' }, gg);
      if (s.pause) el('path', { d: 'M' + (p[0] + 7) + ' ' + (p[1] - 4) + ' v8 M' + (p[0] + 10) + ' ' + (p[1] - 4) + ' v8', 'class': 'lg-ch-pause' }, gg);
      var ttl = el('title', {}, gg); ttl.textContent = 'step ' + (i + 1) + ': ' + label(F, s.node) + (s.note ? ' -- ' + s.note : '');
      gg.addEventListener('click', function () { stop(F); show(F, i + 1); });
    });
  }
  function rlabel(F, r) { return F.g.gById[r] ? F.g.gById[r].label : F.g.byId[r].label; }

  // ---- the frame ----------------------------------------------------------------------------------------------
  function build(fig) {
    var src = fig.querySelector('script[type="application/json"]');
    if (!src) return;
    var g;
    try { g = normalise(JSON.parse(src.textContent)); }
    catch (err) { h('pre', 'lg-error', fig, String(err.message || err)); return; }
    var F = { fig: fig, g: g, id: 'lg' + (++figN), at: 0 };
    if (fig.hasAttribute('data-collapse')) {         // paper: the shape, not the detail, in a 6.5 x 7.4 in box
      g.groups.forEach(function (gr) { gr.collapsed = true; });
      // the box it prints in: a page column by default, or the figure's own (a small card figure says so)
      F.paper = (fig.getAttribute('data-paper') || '624 710').split(' ').map(Number);
    }
    fig.classList.add('lg-ready');
    var head = h('div', 'lg-head', fig);
    var tt = h('div', 'lg-title', head);
    h('span', 'lg-eyebrow', tt, 'agent loop');
    h('span', 'lg-name', tt, g.title || g.id || '');
    F.legend = h('div', 'lg-legend', head);
    var body = h('div', 'lg-body-row', fig);
    F.canvas = h('div', 'lg-canvas', body);
    F.canvas.tabIndex = 0;
    F.canvas.setAttribute('aria-label', (g.title || 'agent loop') + ': graph, left and right arrows step the run');
    F.svg = el('svg', { 'class': 'lg-svg', role: 'img', 'aria-label': g.title || 'agent loop graph' }, F.canvas);
    F.card = h('div', 'lg-card', F.canvas); F.card.hidden = true;
    var side = h('aside', 'lg-side', body);
    F.stepBox = h('div', 'lg-step', side);
    F.limits = h('div', 'lg-limits', side);
    var tabs = h('div', 'lg-tabs', side); tabs.setAttribute('role', 'tablist');
    var panes = h('div', 'lg-panes', side);
    F.stateBox = h('div', 'lg-pane', panes); F.writesBox = h('div', 'lg-pane', panes); F.ckBox = h('div', 'lg-pane', panes);
    [['state', F.stateBox], ['writes', F.writesBox], ['checkpoints', F.ckBox]].forEach(function (t, i) {
      var b = h('button', 'lg-tab', tabs, t[0]);
      b.type = 'button'; b.setAttribute('role', 'tab');
      t[1].setAttribute('role', 'tabpanel');
      function sel() {
        Array.prototype.forEach.call(tabs.children, function (x) { x.setAttribute('aria-selected', 'false'); });
        Array.prototype.forEach.call(panes.children, function (x) { x.hidden = true; });
        b.setAttribute('aria-selected', 'true'); t[1].hidden = false;
      }
      b.addEventListener('click', sel);
      if (i === 0) sel();
    });
    if (g.steps.length) {
      var ctl = h('div', 'lg-ctl', fig);
      var mk = function (lab, aria, fn) { var b = h('button', 'lg-btn', ctl, lab); b.type = 'button'; b.setAttribute('aria-label', aria); b.addEventListener('click', fn); return b; };
      mk('|<', 'to the start', function () { stop(F); show(F, 0); });
      mk('<', 'step back', function () { stop(F); show(F, F.at - 1); });
      F.playBtn = mk('play', 'play', function () { play(F); });
      F.playBtn.classList.add('lg-play');
      mk('>', 'step forward', function () { stop(F); show(F, F.at + 1); });
      mk('>|', 'to the end', function () { stop(F); show(F, g.steps.length); });
      F.scrub = h('input', 'lg-scrub', ctl);
      F.scrub.type = 'range'; F.scrub.min = 0; F.scrub.max = g.steps.length; F.scrub.step = 1; F.scrub.value = 0;
      F.scrub.setAttribute('aria-label', 'run position');
      F.scrub.addEventListener('input', function () { stop(F); show(F, +F.scrub.value); });
      F.chartWrap = h('div', 'lg-chart', fig);
      h('div', 'lg-chart-k', F.chartWrap, 'the run, node by step');
      var cs = h('div', 'lg-chart-scroll', F.chartWrap);
      F.chartSvg = el('svg', { 'class': 'lg-chart-svg', role: 'img', 'aria-label': 'the run, one column per step' }, cs);
      F.canvas.addEventListener('keydown', function (ev) {
        if (ev.key === 'ArrowRight') { ev.preventDefault(); stop(F); show(F, F.at + 1); }
        if (ev.key === 'ArrowLeft') { ev.preventDefault(); stop(F); show(F, F.at - 1); }
      });
    } else {
      F.chartWrap = h('div', 'lg-chart', fig); F.chartWrap.hidden = true;
      F.chartSvg = el('svg', {}, F.chartWrap);
    }
    var cap = fig.querySelector('figcaption');
    if (cap) fig.appendChild(cap);                       // the caption stays last
    draw(F);
    show(F, 0, true);
    if (window.ResizeObserver) new ResizeObserver(function () { fit(F); }).observe(F.canvas);
    fig.loopgraph = F;
    fig.dispatchEvent(new CustomEvent('loopgraph:ready', { bubbles: true, detail: F }));
  }

  function boot() {
    // labels are measured on a canvas, so the page's faces must be in before the first layout (on paper they load late)
    if (document.fonts && document.fonts.status !== 'loaded' && !boot.waited) {
      boot.waited = true;
      document.fonts.ready.then(boot);
      return;
    }
    Array.prototype.forEach.call(document.querySelectorAll('[data-loopgraph]'), function (f) { if (!f.loopgraph) build(f); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
  window.loopgraph = { boot: boot, normalise: normalise };
})();
