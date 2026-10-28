"""Line-art figures for APOLLO style review sheets, after the Apollo Operations Handbook: black ink, no colour, narrow capitals,
dashed fences round subsystems, drums for storage, filled arrowheads. Everything returns SVG text with live fonts
(svg.fonttype none), so the browser sets the lettering in the same faces as the sheet.

  diagram(spec)    block diagrams and graphs from text lines (syntax in diagram's own docstring, as for each below)
  timeline(spec)   rows of bars on one time axis, with vertical markers
  plot(spec, base) CSV series and exact functions, labelled at their ends instead of a legend
  budget(spec)     used-of-capacity gauges (memory, power, link budgets)
  sequence(spec)   messages between actors, top to bottom (protocols, install flows)
  signals(spec)    a timing diagram: clocks, lines and buses on one step axis
  stack(spec)      layers top to bottom: a protocol stack, memory tiers, a memory map with addresses
  bits(spec)       register and packet field layouts, wrapped into rows of N bits
  bars(spec)       categorical bars, grouped or stacked, told apart by hatch
  matrix(spec)     a feature or permission matrix of full, half and open dots, or dots sized by value
  tree(spec)       a hierarchy from an indented outline
  callouts(spec)   leaders from points on a picture to lettering in its margins
  scatter(spec)    points and bubbles, with a least-squares line if asked
  dist(spec)       distributions: box, violin, histogram
  sankey(spec)     flows between stages, ribbons as wide as their values
  treemap(spec)    nested shares as rectangles, from an indented outline
  quadrant(spec)   a 2 by 2 on two axes, quadrants named, points placed
  venn(spec)       two or three overlapping sets, regions lettered
  funnel(spec)     stages narrowing, each with its share of the first
  svg(fig)         any matplotlib figure, styled with STYLE, as SVG text
"""
import ast
import csv
import io
import re
import shlex
from pathlib import Path

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, FancyBboxPatch, Rectangle

INK = "#111111"
LETTER = ["Nimbus Sans Narrow", "Liberation Sans Narrow", "sans-serif"]
STYLE = {
    "svg.fonttype": "none", "font.family": LETTER, "font.size": 7, "axes.edgecolor": INK, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "text.color": INK, "axes.linewidth": 0.8, "lines.linewidth": 0.9,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.direction": "in", "ytick.direction": "in",
    "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": "none", "axes.facecolor": "none",
    "savefig.transparent": True,
}
DASHES = ["-", (0, (5, 2)), (0, (1.2, 1.6)), (0, (6, 2, 1.2, 2)), (0, (2.5, 2.5))]
HATCH = ["////", "", "xxxx", "....", "\\\\\\\\"]


def svg(fig):
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    text = buf.getvalue()
    return text[text.index("<svg"):].strip()


def caps(s):
    return s.replace("\\n", "\n").upper()


def _lines(spec):
    for raw in spec.splitlines():
        raw = raw.strip()
        if raw and not raw.startswith("#"):
            try:
                yield shlex.split(raw)
            except ValueError as e:
                raise SystemExit(f"handbook: cannot read {raw!r} ({e}); quote any label with an apostrophe in it")


# -- block diagram ---------------------------------------------------------------------------------------------------

DX, DY, BW, BH = 1.55, 0.78, 1.15, 0.46            # inches: grid pitch and default box size


def _anchor(n, toward):
    """the point on node n's outline facing `toward` (one of l r t b)"""
    x, y, w, h = n["x"], n["y"], n["w"], n["h"]
    return {"l": (x - w / 2, y), "r": (x + w / 2, y), "t": (x, y + h / 2), "b": (x, y - h / 2)}[toward]


def _hits(pts, others):
    """does the path cross any of the other nodes' boxes (axis-aligned segments only)"""
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        lx, hx, ly, hy = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
        for n in others:
            if lx < n["x"] + n["w"] / 2 and hx > n["x"] - n["w"] / 2 and \
               ly < n["y"] + n["h"] / 2 and hy > n["y"] - n["h"] / 2:
                return True
    return False


def _route(a, b, others=()):
    """an orthogonal path from a to b: straight when they share a row or column, else the first of
    horizontal-then-vertical, vertical-then-horizontal, or a Z through the gap between their rows or columns
    that clears every other box"""
    if abs(a["y"] - b["y"]) < 1e-6:
        s, e = ("r", "l") if b["x"] > a["x"] else ("l", "r")
        return [_anchor(a, s), _anchor(b, e)]
    if abs(a["x"] - b["x"]) < 1e-6:
        s, e = ("b", "t") if b["y"] < a["y"] else ("t", "b")
        return [_anchor(a, s), _anchor(b, e)]
    h = "r" if b["x"] > a["x"] else "l"
    v = "b" if b["y"] < a["y"] else "t"
    back = {"l": "r", "r": "l", "t": "b", "b": "t"}
    p, q = _anchor(a, h), _anchor(b, back[v])
    hv = [p, (q[0], p[1]), q]
    p, q = _anchor(a, v), _anchor(b, back[h])
    vh = [p, (p[0], q[1]), q]
    p, q = _anchor(a, v), _anchor(b, back[v])
    my = (p[1] + q[1]) / 2
    zv = [p, (p[0], my), (q[0], my), q]
    p, q = _anchor(a, h), _anchor(b, back[h])
    mx = (p[0] + q[0]) / 2
    zh = [p, (mx, p[1]), (mx, q[1]), q]
    return next((r for r in (hv, vh, zv, zh) if not _hits(r, others)), hv)


def _bow(a, b, bend):
    """bend as written, made larger for close nodes: arc3 bows by a share of the centre-to-centre distance, and between
    neighbours the boxes hide most of that, so a short edge needs more to read as a curve"""
    chord = ((b["x"] - a["x"]) ** 2 + (b["y"] - a["y"]) ** 2) ** 0.5
    return bend * max(1.0, 2.5 / max(chord, 0.1))


def _crown(a, b, rad):
    """the top of matplotlib's arc3 curve between two node centres"""
    dx, dy = b["x"] - a["x"], b["y"] - a["y"]
    return (a["x"] + b["x"]) / 2 + rad * dy / 2, (a["y"] + b["y"]) / 2 - rad * dx / 2


def diagram(spec):
    """node ID "LABEL" COL ROW [box|drum|round|dash|diamond|text] [w=COLS] [h=ROWS]
                                                (diamond: a decision; its edges leave from the points)
       edge FROM TO ["LABEL"] [dash] [both]     (routed round other boxes: one elbow, else a Z through a gap)
       edge FROM TO ["LABEL"] bend=R            (a curve instead, bowed by R: + bows to the right of the way it
                                                 runs, - to the left; for back-edges and cycles through a graph)
       loop ID ["LABEL"] [top|bottom]           (an edge from a node back to itself)
       edge FROM TO ... ends=1:N                (lettering at each end: cardinality for an ER model, 1:1 1:N N:M)
       fence "LABEL" ID ID ...
       note COL ROW "TEXT"                      (small free lettering)
       grid DX DY                               (inches between columns and rows; default 1.55 0.78)
       lane "LABEL" ROW [ROWS]                  (a swimlane: a band across the diagram over that row (and the
                                                 next ROWS-1), its owner lettered at the left; for who-does-what)"""
    global DX, DY
    nodes, edges, fences, notes, loops, lanes = {}, [], [], [], [], []
    keep = DX, DY
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "grid":
            DX, DY = float(rest[0]), float(rest[1])
        elif kind == "node":
            opts = dict(o.split("=") for o in rest[4:] if "=" in o)
            shape = next((o for o in rest[4:] if "=" not in o), "box")
            nodes[rest[0]] = dict(label=caps(rest[1]), x=float(rest[2]) * DX, y=-float(rest[3]) * DY, shape=shape,
                                  w=float(opts.get("w", 0)) * DX - (DX - BW) if "w" in opts else BW,
                                  h=float(opts.get("h", 0)) * DY - (DY - BH) if "h" in opts else BH)
        elif kind == "edge":
            label = next((o for o in rest[2:] if o not in ("dash", "both") and "=" not in o), "")
            ends = next((o[5:].split(":") for o in rest[2:] if o.startswith("ends=")), None)
            bend = next((float(o[5:]) for o in rest[2:] if o.startswith("bend=")), None)
            edges.append(dict(a=rest[0], b=rest[1], label=caps(label), dash="dash" in rest[2:], both="both" in rest[2:],
                              bend=bend, ends=ends))
        elif kind == "loop":
            loops.append((rest[0], caps(next((o for o in rest[1:] if o not in ("top", "bottom")), "")),
                          "bottom" in rest[1:]))
        elif kind == "fence":
            fences.append(dict(label=caps(rest[0]), ids=rest[1:]))
        elif kind == "lane":
            lanes.append((caps(rest[0]), float(rest[1]), float(rest[2]) if len(rest) > 2 else 1.0))
        elif kind == "note":
            notes.append((float(rest[0]) * DX, -float(rest[1]) * DY, caps(rest[2])))
    xs = [n["x"] + s * n["w"] / 2 for n in nodes.values() for s in (-1, 1)] + [x for x, _, _ in notes]
    ys = [n["y"] + s * n["h"] / 2 for n in nodes.values() for s in (-1, 1)] + [y for _, y, _ in notes]
    for e in edges:                                # a curve's crown can stand outside the boxes
        if e["bend"] is not None:
            cx, cy = _crown(nodes[e["a"]], nodes[e["b"]], _bow(nodes[e["a"]], nodes[e["b"]], e["bend"]))
            xs.append(cx); ys.append(cy)
    for k, _, under in loops:
        ys.append(nodes[k]["y"] + (-1 if under else 1) * (nodes[k]["h"] / 2 + 0.42))
    pad = 0.35
    x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    if lanes:                                        # room at the left for the lanes' owners, and their full height
        x0 -= 0.55
        y0 = min(y0, min(-(r + n - 0.5) * DY for _, r, n in lanes))
        y1 = max(y1, max(-(r - 0.5) * DY for _, r, _ in lanes))
    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=(x1 - x0, y1 - y0))
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_axis_off()
        for label, r, n in lanes:
            top, bot = -(r - 0.5) * DY, -(r + n - 0.5) * DY
            ax.plot([x0 + 0.05, x1 - 0.05], [top, top], color=INK, lw=0.6)
            ax.plot([x0 + 0.05, x1 - 0.05], [bot, bot], color=INK, lw=0.6)
            ax.plot([x0 + 0.42] * 2, [top, bot], color=INK, lw=0.6)
            ax.text(x0 + 0.24, (top + bot) / 2, label, fontsize=5.8, rotation=90, ha="center", va="center",
                    fontweight="bold")
        for f in fences:
            m = [nodes[i] for i in f["ids"]]
            fx0 = min(n["x"] - n["w"] / 2 for n in m) - 0.14
            fx1 = max(n["x"] + n["w"] / 2 for n in m) + 0.14
            fy0 = min(n["y"] - n["h"] / 2 for n in m) - 0.14
            fy1 = max(n["y"] + n["h"] / 2 for n in m) + 0.22
            ax.add_patch(Rectangle((fx0, fy0), fx1 - fx0, fy1 - fy0, fill=False, ec=INK, lw=0.8, ls=(0, (6, 3))))
            ax.text(fx0 + 0.06, fy1 - 0.05, f["label"], fontsize=5.6, va="top", ha="left")
        for e in (e for e in edges if e["bend"] is None):
            pts = _route(nodes[e["a"]], nodes[e["b"]], [n for k, n in nodes.items() if k not in (e["a"], e["b"])])
            ls = (0, (4, 2.5)) if e["dash"] else "-"
            for p, q in zip(pts[:-2], pts[1:-1]):
                ax.plot([p[0], q[0]], [p[1], q[1]], color=INK, lw=0.8, ls=ls, solid_capstyle="butt")
            style = "<|-|>" if e["both"] else "-|>"
            ax.annotate("", xy=pts[-1], xytext=pts[-2], arrowprops=dict(arrowstyle=style, color=INK, lw=0.8, ls=ls,
                                                                         mutation_scale=7, shrinkA=0, shrinkB=0))
            for (px, py), (qx, qy), mark in ((pts[0], pts[1], e["ends"] and e["ends"][0]),
                                             (pts[-1], pts[-2], e["ends"] and e["ends"][1])):
                if mark:                             # beside the line, a little way out from the box
                    dx, dy = np.sign(qx - px), np.sign(qy - py)
                    ax.text(px + dx * 0.1 + (0 if dx else 0.06), py + dy * 0.1 + (0.05 if dx else 0), mark,
                            fontsize=5.6, ha="center" if dx else "left", va="bottom" if dx else "center")
            if e["label"]:
                seg = max(zip(pts[:-1], pts[1:]), key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
                mx, my = (seg[0][0] + seg[1][0]) / 2, (seg[0][1] + seg[1][1]) / 2
                flat = abs(seg[1][1] - seg[0][1]) < 1e-6
                label = e["label"]
                if flat and "\n" not in label and " " in label and len(label) * 0.042 > abs(seg[1][0] - seg[0][0]):
                    words = label.split(" ")              # wider than its run: two lines, so it stays off the boxes
                    cut = min(range(1, len(words)), key=lambda k: abs(len(" ".join(words[:k])) - len(label) / 2))
                    label = " ".join(words[:cut]) + "\n" + " ".join(words[cut:])
                ax.text(mx, my + (0.05 if flat else 0), label, fontsize=5.2, ha="center" if flat else "left",
                        va="bottom" if flat else "center", linespacing=1.05,
                        bbox=None if flat else dict(fc="white", ec="none", pad=0.6))
        for n in nodes.values():
            x, y, w, h = n["x"], n["y"], n["w"], n["h"]
            if n["shape"] == "drum":
                e = 0.09
                ax.add_patch(Rectangle((x - w / 2, y - h / 2 + e / 2), w, h - e, fc="white", ec="none"))
                ax.plot([x - w / 2] * 2, [y - h / 2 + e / 2, y + h / 2 - e / 2], color=INK, lw=0.9)
                ax.plot([x + w / 2] * 2, [y - h / 2 + e / 2, y + h / 2 - e / 2], color=INK, lw=0.9)
                ax.add_patch(Ellipse((x, y - h / 2 + e / 2), w, e, fc="white", ec=INK, lw=0.9))
                ax.add_patch(Rectangle((x - w / 2 + 0.01, y - h / 2 + e / 2), w - 0.02, 0.02, fc="white", ec="none"))
                ax.add_patch(Ellipse((x, y + h / 2 - e / 2), w, e, fc="white", ec=INK, lw=0.9))
            elif n["shape"] == "diamond":
                n["patch"] = ax.add_patch(plt.Polygon([(x - w / 2, y), (x, y + h / 2), (x + w / 2, y), (x, y - h / 2)],
                                                      closed=True, fc="white", ec=INK, lw=0.9))
            elif n["shape"] != "text":
                rad = 0.08 if n["shape"] == "round" else 0.0
                n["patch"] = ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                                         boxstyle=f"round,pad=0,rounding_size={rad}", fc="white", ec=INK,
                                                         lw=0.9, ls=(0, (4, 2)) if n["shape"] == "dash" else "-"))
            ax.text(x, y - (0.02 if n["shape"] == "drum" else 0), n["label"], ha="center", va="center", fontsize=6,
                    linespacing=1.1)
        arrow = dict(color=INK, lw=0.8, mutation_scale=7, zorder=0.9)
        for e in (e for e in edges if e["bend"] is not None):
            a, b = nodes[e["a"]], nodes[e["b"]]
            ax.add_patch(FancyArrowPatch((a["x"], a["y"]), (b["x"], b["y"]), patchA=a.get("patch"), patchB=b.get("patch"),
                                         connectionstyle=f"arc3,rad={_bow(a, b, e['bend'])}",
                                         ls=(0, (4, 2.5)) if e["dash"] else "-",
                                         arrowstyle="<|-|>" if e["both"] else "-|>", shrinkA=2, shrinkB=1, **arrow))
            if e["label"]:
                ax.text(*_crown(a, b, _bow(a, b, e["bend"])), e["label"], fontsize=5.2, ha="center", va="center",
                        linespacing=1.05,
                        bbox=dict(fc="white", ec="none", pad=0.6))
        for k, label, under in loops:
            n = nodes[k]
            sgn = -1 if under else 1
            y = n["y"] + sgn * n["h"] / 2
            ax.add_patch(FancyArrowPatch((n["x"] - n["w"] / 4, y), (n["x"] + n["w"] / 4, y), arrowstyle="-|>",
                                         connectionstyle=f"arc3,rad={-1.3 * sgn}", shrinkA=0, shrinkB=0, **arrow))
            if label:
                ax.text(n["x"], y + sgn * (0.65 * n["w"] / 2 + 0.03), label, fontsize=5.2, ha="center",
                        va="bottom" if sgn > 0 else "top")
        for x, y, text in notes:
            ax.text(x, y, text, ha="center", va="center", fontsize=5.2, linespacing=1.1)
        DX, DY = keep
        return svg(fig)


# -- timeline --------------------------------------------------------------------------------------------------------

def timeline(spec):
    """axis "LABEL" START END [ticks=STEP]
       bar "ROW" START END [hatch|open|solid] ["NOTE"]
       mark AT "LABEL" [dash]
       call ROW AT "TEXT"                       (a leader from the bar row to lettering below the axis)
       milestone "ROW" AT ["LABEL"]             (a black diamond on that row: a date that has no length)
       after "ROW A" "ROW B"                    (an arrow from the end of A's last bar to the start of B's first:
                                                 a dependency, as on a Gantt chart)"""
    rows, bars, marks, calls, stones, deps = [], [], [], [], [], []
    axis = dict(label="", lo=0.0, hi=1.0, step=None)
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "axis":
            axis = dict(label=caps(rest[0]), lo=float(rest[1]), hi=float(rest[2]), step=None)
            for o in rest[3:]:
                if o.startswith("ticks="):
                    axis["step"] = float(o[6:])
        elif kind == "bar":
            if rest[0] not in rows:
                rows.append(rest[0])
            fill = next((o for o in rest[3:] if o in ("hatch", "open", "solid")), "open")
            note = next((o for o in rest[3:] if o not in ("hatch", "open", "solid")), "")
            bars.append((rest[0], float(rest[1]), float(rest[2]), fill, caps(note)))
        elif kind == "mark":
            marks.append((float(rest[0]), caps(rest[1]), "dash" in rest[2:]))
        elif kind == "call":
            calls.append((rest[0], float(rest[1]), caps(rest[2])))
        elif kind == "milestone":
            if rest[0] not in rows:
                rows.append(rest[0])
            stones.append((rest[0], float(rest[1]), caps(rest[2]) if len(rest) > 2 else ""))
        elif kind == "after":
            deps.append((rest[0], rest[1]))
    rh = 0.22
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(5.6, 0.55 + rh * len(rows) + (0.3 if marks else 0)))
        for row, a, b, fill, note in bars:
            y = -rows.index(row)
            ax.add_patch(Rectangle((a, y - 0.32), b - a, 0.64, fc=INK if fill == "solid" else "white", ec=INK, lw=0.7,
                                   hatch="//////" if fill == "hatch" else None))
            if note:
                ax.text(b + (axis["hi"] - axis["lo"]) * 0.008, y, note, fontsize=5.2, va="center")
        for at, label, dash in marks:
            ax.axvline(at, color=INK, lw=0.7, ls=(0, (3, 2)) if dash else "-")
            ax.text(at, 0.75, label, fontsize=5.4, ha="center", va="bottom")
        for row, at, text in calls:
            y = -rows.index(row)
            ax.annotate(text, xy=(at, y - 0.32), xytext=(at, -len(rows) + 0.05), fontsize=5.2, ha="center", va="top",
                        arrowprops=dict(arrowstyle="-", color=INK, lw=0.5))
        for row, at, label in stones:
            y = -rows.index(row)
            ax.plot([at], [y], marker="D", ms=5, mfc=INK, mec=INK, zorder=4)
            if label:
                ax.text(at + (axis["hi"] - axis["lo"]) * 0.012, y, label, fontsize=5.2, va="center")
        for a, b in deps:
            ea = max(e for r, _, e, _, _ in bars if r == a)
            sb = min(st for r, st, _, _, _ in bars if r == b)
            ya, yb = -rows.index(a), -rows.index(b)
            ax.annotate("", xy=(sb, yb + (0.32 if yb < ya else -0.32)), xytext=(ea, ya),
                        arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.6, mutation_scale=6, shrinkA=0, shrinkB=0,
                                        connectionstyle="angle,angleA=0,angleB=90,rad=0"))
        ax.set_yticks([-i for i in range(len(rows))], [caps(r) for r in rows])
        ax.set_ylim(-len(rows) + 0.4, 0.7)
        ax.set_xlim(axis["lo"], axis["hi"])
        if axis["step"]:
            n = int(round((axis["hi"] - axis["lo"]) / axis["step"]))
            ax.set_xticks([axis["lo"] + i * axis["step"] for i in range(n + 1)])
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.set_xlabel(axis["label"], fontsize=6)
        return svg(fig)


# -- plot: CSV columns and exact functions ---------------------------------------------------------------------------

# what a fn expression may name: x, and these
FN = {k: getattr(np, k) for k in ("sin", "cos", "tan", "arctan", "exp", "log", "log10", "log2", "sqrt", "abs",
                                  "sinh", "cosh", "tanh", "where", "minimum", "maximum", "clip", "floor", "ceil",
                                  "sign", "pi", "e", "hypot", "arctan2", "sinc", "degrees", "radians")}


class _Floats(ast.NodeTransformer):
    """integer constants to floats, so 10**10**10 overflows at once instead of building a vast integer"""
    def visit_Constant(self, node):
        return ast.copy_location(ast.Constant(float(node.value)), node) if type(node.value) is int else node


def _fn(src, xs, **more):
    """y for a fn line: arithmetic on x (and any arrays named in more), numbers and the FN names only; nothing else
    is evaluated"""
    env = {"x": xs, **more}
    tree = ast.parse(src, mode="eval")
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Compare, ast.Call, ast.Name, ast.Load, ast.Constant,
               ast.operator, ast.unaryop, ast.cmpop)
    for node in ast.walk(tree):
        bad = (not isinstance(node, allowed)
               or isinstance(node, ast.Name) and node.id not in env and node.id not in FN
               or isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.keywords)
               or isinstance(node, ast.Constant) and type(node.value) not in (int, float))
        if bad:
            raise SystemExit(f"handbook: fn {src!r}: only {' '.join(env)}, numbers, + - * / ** < > and "
                             f"{' '.join(sorted(FN))}")
    code = compile(ast.fix_missing_locations(_Floats().visit(tree)), "<fn>", "eval")
    with np.errstate(all="ignore"):
        return np.broadcast_to(np.asarray(eval(code, {"__builtins__": {}}, {**FN, **env}), dtype=float), xs.shape)


def plot(spec, base=Path(".")):
    """csv PATH                         (relative to the sheet)
       x COLUMN ["LABEL"]
       y COLUMN ["LABEL"] [dots|step|area] [every=N] [err=COLUMN]   (a series; dots for measured points, step for a
                                        staircase, err= for error bars of that half-width,
                                        area to stack it as a hatched band on the area series before it;
                                        every=N keeps every Nth row, so dense dots stay dots)
       percent                          (the panel's area series as shares of their sum, 0 to 100)
       fn "EXPR" ["LABEL"] [dots|step]  (an exact curve y(x) in numpy terms: sin exp sqrt log10 pi where ...)
       range LO HI [N]                  (x for fn curves; default the csv's x, else 0..1; N points, default 400)
       xlabel "LABEL" / ylabel "LABEL"
       xlim LO HI / ylim LO HI
       log x|y|xy
       mark AT "LABEL"                  (vertical line at x = AT, through every panel)
       hline AT "LABEL"                 (horizontal line at y = AT: a limit, a threshold)
       panel                            (start another panel below, on the same x: a Bode plot's phase, a
                                         spectrum under its waveform; y, fn, ylabel, ylim, hline and log y
                                         after it belong to the new panel)
       size wide | size W H             (inches; default 3.4 x 2.2, wide 6.4 x 2.4; a panel more adds 0.6 of H)
     every series is labelled at its right end, so there is no legend to look up"""
    cols, marks = {}, []
    panels = [dict(series=[], hlines=[], ylabel="", ylim=None, logy=False, percent=False)]
    xcol, xlabel, logx, rng, xlim, size = None, "", False, None, None, (3.4, 2.2)
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        cur = panels[-1]
        flags = [o for o in rest[1:] if o in ("dots", "step", "area") or o.startswith(("every=", "err="))]
        words = [o for o in rest[1:] if o not in flags]
        if kind == "csv":
            with open(base / rest[0], newline="") as fh:
                for row in csv.DictReader(fh):
                    for k, v in row.items():
                        cols.setdefault(k, []).append(v)        # to numbers when used, so text columns are fine
        elif kind == "x":
            xcol, xlabel = rest[0], caps(rest[1] if len(rest) > 1 else rest[0])
        elif kind in ("y", "fn"):
            cur["series"].append((kind, rest[0], caps(words[0]) if words else ("" if kind == "fn" else caps(rest[0])),
                                  flags))
        elif kind == "range":
            rng = (float(rest[0]), float(rest[1]), int(rest[2]) if len(rest) > 2 else 400)
        elif kind == "xlabel":
            xlabel = caps(rest[0])
        elif kind == "ylabel":
            cur["ylabel"] = caps(rest[0])
        elif kind == "xlim":
            xlim = (float(rest[0]), float(rest[1]))
        elif kind == "ylim":
            cur["ylim"] = (float(rest[0]), float(rest[1]))
        elif kind == "log":
            logx = logx or "x" in rest[0]
            cur["logy"] = "y" in rest[0]
        elif kind == "mark":
            marks.append((float(rest[0]), caps(rest[1])))
        elif kind == "hline":
            cur["hlines"].append((float(rest[0]), caps(rest[1]) if len(rest) > 1 else ""))
        elif kind == "panel":
            panels.append(dict(series=[], hlines=[], ylabel="", ylim=None, logy=False, percent=False))
        elif kind == "percent":
            cur["percent"] = True
        elif kind == "size":
            size = (6.4, 2.4) if rest[0] == "wide" else (float(rest[0]), float(rest[1]))
    if rng:
        lo, hi, n = rng
        xs = np.geomspace(lo, hi, n) if logx else np.linspace(lo, hi, n)
    else:
        xs = np.asarray(cols[xcol], dtype=float) if xcol else np.linspace(0, 1, 400)
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(len(panels), 1, sharex=True, squeeze=False,
                                 figsize=(size[0], size[1] * (1 + 0.6 * (len(panels) - 1))))
        for pi_, (ax, pnl) in enumerate(zip(axes[:, 0], panels)):
            data = []
            for kind, src, label, flags in pnl["series"]:
                if kind == "y":
                    k = next((int(f[6:]) for f in flags if f.startswith("every=")), 1)
                    data.append((np.asarray(cols[xcol], dtype=float)[::k], np.asarray(cols[src], dtype=float)[::k]))
                else:
                    data.append((xs, _fn(src, xs)))
            areas = [d for d, (_, _, _, f) in zip(data, pnl["series"]) if "area" in f]
            whole = sum(y for _, y in areas) if pnl["percent"] and areas else None
            under, band = None, 0
            for i, ((kind, src, label, flags), (x, y)) in enumerate(zip(pnl["series"], data)):
                if "area" in flags:
                    y = 100 * y / whole if whole is not None else y
                    lo = under if under is not None else np.zeros_like(y)
                    hi = lo + y
                    ax.fill_between(x, lo, hi, facecolor="white", edgecolor=INK, linewidth=0.6,
                                    hatch=["//////", "", "xxxx", "....", "\\\\\\"][band % 5])
                    band += 1
                    under = hi
                    if label:
                        ax.annotate(label, xy=(x[-1], (lo[-1] + hi[-1]) / 2), xytext=(4, 0),
                                    textcoords="offset points", fontsize=5.6, va="center", annotation_clip=False)
                    continue
                err = next((f[4:] for f in flags if f.startswith("err=")), None)
                if err:
                    k = next((int(f[6:]) for f in flags if f.startswith("every=")), 1)
                    ax.errorbar(x, y, yerr=np.asarray(cols[err], dtype=float)[::k], fmt="none", ecolor=INK,
                                elinewidth=0.6, capsize=1.8, capthick=0.6)
                if "dots" in flags:
                    ax.plot(x, y, ls="none", marker="o", ms=2.6, mfc="white", mec=INK, mew=0.7)
                else:
                    ax.plot(x, y, color=INK, ls=DASHES[i % len(DASHES)],
                            drawstyle="steps-post" if "step" in flags else "default")
                if label:
                    ax.annotate(label, xy=(x[-1], y[-1]), xytext=(4, 0), textcoords="offset points", fontsize=5.6,
                                va="center", annotation_clip=False)
            for at, label in marks:
                ax.axvline(at, color=INK, lw=0.6, ls=(0, (3, 2)))
                if pi_ == 0:
                    ax.text(at, 1.0, label, fontsize=5.4, ha="center", va="bottom", transform=ax.get_xaxis_transform())
            for at, label in pnl["hlines"]:
                ax.axhline(at, color=INK, lw=0.6, ls=(0, (3, 2)))
                # letter it at the end where the curves stand farthest from the line
                ends = [(l.get_ydata()[0], l.get_ydata()[-1]) for l in ax.get_lines() if len(l.get_ydata()) > 1]
                left = sum(abs(a - at) for a, _ in ends) > sum(abs(b - at) for _, b in ends)
                ax.text(0.01 if left else 0.99, at, label, fontsize=5.4, ha="left" if left else "right", va="bottom",
                        transform=ax.get_yaxis_transform(), bbox=dict(fc="white", ec="none", pad=0.4))
            if logx:
                ax.set_xscale("log")
            if pnl["logy"]:
                ax.set_yscale("log")
            if xlim:
                ax.set_xlim(*xlim)
            if pnl["ylim"]:
                ax.set_ylim(*pnl["ylim"])
            ax.grid(True, color=INK, lw=0.25, alpha=0.35)
            ax.set_ylabel(pnl["ylabel"], fontsize=6)
        axes[-1, 0].set_xlabel(xlabel, fontsize=6)
        fig.align_ylabels(axes[:, 0])
        return svg(fig)


# -- budget gauges ---------------------------------------------------------------------------------------------------

def _num(v):
    """69540 -> 69 540, the handbook's grouping"""
    return f"{v:,.0f}".replace(",", " ") if float(v).is_integer() else f"{v:,g}".replace(",", " ")


def _value(v):
    """a number, hex (0x8DFBC, 0X10) read as hex"""
    return float(int(v, 16)) if v.lower().startswith("0x") else float(v)


def budget(spec):
    """bar "LABEL" USED CAPACITY ["UNIT"]  (one gauge a line: the used part hatched, headroom open, figures at the end;
                                          numbers may be hex, 0x8DFBC)
       mark PERCENT "LABEL"               (a dashed limit across every gauge, e.g. 90 "RED AT 90 %")"""
    bars, marks = [], []
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "bar":
            if _value(rest[2]) <= 0:
                raise SystemExit(f"handbook: budget {rest[0]!r} has no capacity")
            bars.append((caps(rest[0]), _value(rest[1]), _value(rest[2]),
                         rest[3] if len(rest) > 3 else ""))
        elif kind == "mark":
            marks.append((float(rest[0]), caps(rest[1])))
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(6.4, 0.3 + 0.3 * len(bars) + (0.15 if marks else 0)))
        for i, (label, used, cap, unit) in enumerate(bars):
            y = -i
            ax.add_patch(Rectangle((0, y - 0.3), 1, 0.6, fc="white", ec=INK, lw=0.8))
            ax.add_patch(Rectangle((0, y - 0.3), min(used / cap, 1), 0.6, fc="white", ec=INK, lw=0.6, hatch="//////"))
            ax.text(-0.02, y, label, ha="right", va="center", fontsize=6)
            ax.text(1.02, y, f"{_num(used)} OF {_num(cap)} {unit.upper()}".rstrip() + f",  {100 * used / cap:.1f} %",
                    ha="left", va="center", fontsize=5.8)
        for pct, label in marks:
            ax.plot([pct / 100] * 2, [-len(bars) + 0.6, 0.45], color=INK, lw=0.7, ls=(0, (3, 2)))
            ax.text(pct / 100, 0.5, label, ha="center", va="bottom", fontsize=5.4)
        ax.set_xlim(-0.42, 1.55); ax.set_ylim(-len(bars) + 0.5, 0.5 + (0.45 if marks else 0.05))
        ax.set_axis_off()
        return svg(fig)


# -- sequence chart --------------------------------------------------------------------------------------------------

def sequence(spec):
    """actor ID "LABEL"                  (columns, left to right in the order given)
       msg FROM TO "LABEL" [dash]        (one step each, top to bottom; FROM == TO is a call to itself; dash for replies)
       note ID "TEXT"                    (boxed lettering on that lifeline, one step)
       gap ["TEXT"]                      (time passes: the lifelines break for a step)"""
    actors, steps = {}, []
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "actor":
            actors[rest[0]] = (len(actors), caps(rest[1]))
        elif kind == "msg":
            steps.append(("msg", rest[0], rest[1], caps(rest[2]) if len(rest) > 2 else "", "dash" in rest[3:]))
        elif kind == "note":
            steps.append(("note", rest[0], None, caps(rest[1]), False))
        elif kind == "gap":
            steps.append(("gap", None, None, caps(rest[0]) if rest else "", False))
    dx, dy = 1.6, 0.3
    n = len(steps)
    X = {k: i * dx for k, (i, _) in actors.items()}
    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=((len(actors) - 1) * dx + 1.6, (n + 1.6) * dy))
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
        ax.set_xlim(-0.8, (len(actors) - 1) * dx + 0.8); ax.set_ylim(-(n + 0.8) * dy, 0.05 + 0.336 + 0.06)
        gaps = [k for k, s in enumerate(steps) if s[0] == "gap"]
        for k, (i, label) in actors.items():
            x = X[k]
            ax.add_patch(Rectangle((x - 0.55, 0.05), 1.1, 0.42 * 0.8, fc="white", ec=INK, lw=0.9))
            ax.text(x, 0.05 + 0.168, label, ha="center", va="center", fontsize=6, linespacing=1.05)
            y = 0.05
            for g in gaps + [n]:
                yb = -(g + 0.25) * dy if g < n else -(n + 0.4) * dy
                ax.plot([x, x], [y, yb], color=INK, lw=0.6)
                y = -(g + 0.75) * dy
        for k, (kind, a, b, label, dash) in enumerate(steps):
            y = -(k + 0.5) * dy
            if kind == "gap":
                for x in X.values():
                    ax.plot([x - 0.08, x + 0.08], [y + 0.06, y + 0.1], color=INK, lw=0.6)
                    ax.plot([x - 0.08, x + 0.08], [y - 0.1, y - 0.06], color=INK, lw=0.6)
                if label:
                    ax.text(X[next(iter(actors))] + 0.15, y, label, fontsize=5.2, va="center", style="italic")
            elif kind == "note":
                ax.text(X[a], y, label, ha="center", va="center", fontsize=5.2, linespacing=1.05,
                        bbox=dict(fc="white", ec=INK, lw=0.6, boxstyle="square,pad=0.35"))
            elif a == b:
                x = X[a]
                ax.plot([x, x + 0.3, x + 0.3], [y + 0.08, y + 0.08, y - 0.08], color=INK, lw=0.7,
                        ls=(0, (4, 2.5)) if dash else "-")
                ax.annotate("", xy=(x, y - 0.08), xytext=(x + 0.3, y - 0.08),
                            arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.7, mutation_scale=6, shrinkA=0, shrinkB=0))
                ax.text(x + 0.36, y, label, fontsize=5.2, va="center")
            else:
                ax.annotate("", xy=(X[b], y - 0.06), xytext=(X[a], y - 0.06),
                            arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.7, ls=(0, (4, 2.5)) if dash else "-",
                                            mutation_scale=7, shrinkA=0, shrinkB=0))
                ax.text((X[a] + X[b]) / 2, y - 0.03, label, ha="center", va="bottom", fontsize=5.2,
                        bbox=dict(fc="white", ec="none", pad=0.3))       # over any lifeline it crosses
        return svg(fig)


# -- timing diagram --------------------------------------------------------------------------------------------------

def signals(spec):
    """signal "NAME" WAVE ["D0,D1,..."]   (one row a line; WAVE has one character a clock step:
                                         0 1 low, high   p n a clock period, high or low first   . hold   z released (mid level)
                                         x unknown (hatched)   = a bus value, lettered from the list in order)
       mark STEP "LABEL" [dash]          (a vertical line at that step, labelled above)"""
    rows, marks = [], []
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "signal":
            rows.append((caps(rest[0]), rest[1], rest[2].split(",") if len(rest) > 2 else []))
        elif kind == "mark":
            marks.append((float(rest[0]), caps(rest[1]), "dash" in rest[2:]))
    steps = max(len(w) for _, w, _ in rows)
    half = {"0": "00", "1": "11", "p": "10", "n": "01", "z": "zz", "x": "xx", "=": "=.", ".": ".."}
    h, s = 0.5, 0.06                                       # level height and edge slant, in steps
    level = {"0": 0.0, "1": h, "z": h / 2}
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(6.4, 0.3 + 0.36 * len(rows) + (0.15 if marks else 0)))
        for r, (name, wave, data) in enumerate(rows):
            base = -r * 0.9
            runs = []                                      # [state, start, end, label]
            last = "x"
            bad = set(wave) - set(half)
            if bad:
                raise SystemExit(f"handbook: signal {name!r}: unknown wave characters {''.join(sorted(bad))!r}")
            for k, ch in enumerate("".join(half[c] for c in wave)):
                t = k / 2
                if ch == "." and not runs:               # nothing to hold yet: unknown
                    ch = "x"
                if ch == "." or (ch == last and ch != "=" and runs):
                    runs[-1][2] = t + 0.5
                    continue
                last = ch
                runs.append([ch, t, t + 0.5, data.pop(0).upper() if ch == "=" and data else ""])
            for j, (st, a, b, label) in enumerate(runs):
                first, final = j == 0, j == len(runs) - 1
                if st in level:
                    y = base + level[st]
                    ax.plot([a if first else a + s, b if final else b - s], [y, y], color=INK, lw=0.8,
                            ls=(0, (2, 1.5)) if st == "z" else "-")
                else:
                    lo, mid, hi = base, base + h / 2, base + h
                    left = [(a, lo), (a, hi)] if first else [(a, mid), (a + s, hi)]
                    right = [(b, hi), (b, lo)] if final else [(b - s, hi), (b, mid), (b - s, lo)]
                    pts = left + right + ([(a + s, lo)] if not first else [])
                    ax.add_patch(plt.Polygon(pts, closed=True, fc="white", ec=INK, lw=0.8,
                                             hatch="//////" if st == "x" else None))
                    if label:
                        ax.text((a + b) / 2, mid, label, ha="center", va="center", fontsize=5.4)
                if not final:
                    nx = runs[j + 1][0]
                    if st in level and nx in level:
                        ax.plot([b - s, b + s], [base + level[st], base + level[nx]], color=INK, lw=0.8)
                    elif st in level:
                        ax.plot([b - s, b], [base + level[st], base + h / 2], color=INK, lw=0.8)
                    elif nx in level:
                        ax.plot([b, b + s], [base + h / 2, base + level[nx]], color=INK, lw=0.8)
            ax.text(-0.3, base + h / 2, name, ha="right", va="center", fontsize=6)
        top, prev, lift = 0.75, None, 0.0
        for at, label, dash in sorted(marks):
            lift = 0.3 - lift if prev is not None and at - prev < 2 else 0.0      # stagger marks that crowd
            prev = at
            ax.plot([at, at], [-(len(rows) - 1) * 0.9 - 0.15, top + lift], color=INK, lw=0.6,
                    ls=(0, (3, 2)) if dash else "-")
            ax.text(at, top + lift + 0.05, label, ha="center", va="bottom", fontsize=5.4)
        ax.set_xlim(-2.2, steps + 0.2); ax.set_ylim(-(len(rows) - 1) * 0.9 - 0.25, top + (0.65 if marks else 0))
        ax.set_axis_off()
        return svg(fig)


# -- layer stack and memory map --------------------------------------------------------------------------------------

def stack(spec):
    """layer "LABEL" ["NOTE"] [open|hatch|dash|solid] [h=N] [at="TEXT"]
                                     (top to bottom; h in units of a layer; at= is lettered at the layer's top edge,
                                      on the left: an address, a tier's latency)
       span FIRST LAST "LABEL"       (a bracket at the right over layers FIRST..LAST, counted from 1)
       width W                       (inches; default 3)"""
    layers, spans, width = [], [], 3.0
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "layer":
            opts = dict(o.split("=", 1) for o in rest[1:] if "=" in o)
            words = [o for o in rest[1:] if "=" not in o and o not in ("open", "hatch", "dash", "solid")]
            fill = next((o for o in rest[1:] if o in ("open", "hatch", "dash", "solid")), "open")
            layers.append(dict(label=caps(rest[0]), note=caps(words[0]) if words else "", fill=fill,
                               h=float(opts.get("h", 1)), at=opts.get("at", "")))
        elif kind == "span":
            spans.append((int(rest[0]) - 1, int(rest[1]) - 1, caps(rest[2])))
        elif kind == "width":
            width = float(rest[0])
    unit = 0.36
    top = [0.0]
    for l in layers:
        top.append(top[-1] - l["h"] * unit)
    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=(width + 2.6, -top[-1] + 0.2))
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
        ax.set_xlim(-1.2, width + 1.4); ax.set_ylim(top[-1] - 0.1, 0.1)
        for i, l in enumerate(layers):
            y0, y1 = top[i + 1], top[i]
            solid = l["fill"] == "solid"
            ax.add_patch(Rectangle((0, y0), width, y1 - y0, fc=INK if solid else "white", ec=INK, lw=0.9,
                                   hatch="//////" if l["fill"] == "hatch" else None,
                                   ls=(0, (4, 2)) if l["fill"] == "dash" else "-"))
            ym = (y0 + y1) / 2
            if l["fill"] == "hatch":                 # a clear plate for the lettering, so the hatch stays round it
                ax.add_patch(Rectangle((width * 0.2, ym - 0.14), width * 0.6, 0.28, fc="white", ec="none"))
            txt = dict(ha="center", va="center", color="white" if solid else INK)
            if l["note"]:
                ax.text(width / 2, ym + 0.06, l["label"], fontsize=6.4, **txt)
                ax.text(width / 2, ym - 0.08, l["note"], fontsize=5.2, **txt)
            else:
                ax.text(width / 2, ym, l["label"], fontsize=6.4, **txt)
            if l["at"]:
                ax.plot([-0.08, 0], [y1, y1], color=INK, lw=0.6)
                ax.text(-0.12, y1, l["at"], fontsize=5.4, ha="right", va="center")       # 0x stays lower case
        for a, b, label in spans:
            y1, y0 = top[a] - 0.03, top[b + 1] + 0.03
            x = width + 0.12
            ax.plot([x, x + 0.08, x + 0.08, x], [y1, y1, y0, y0], color=INK, lw=0.7)
            ax.text(x + 0.14, (y0 + y1) / 2, label, fontsize=5.6, va="center", ha="left", linespacing=1.1)
        return svg(fig)


# -- bit fields ------------------------------------------------------------------------------------------------------

def bits(spec):
    """width N                       (bits a row; default 32)
       numbers down|up               (down: N-1 at the left, a register's way; up: 0 at the left, an RFC's; default down)
       field "NAME" BITS [hatch]     (left to right, wrapping into rows; hatch for reserved)"""
    width, numbers, fields = 32, "down", []
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "width":
            width = int(rest[0])
        elif kind == "numbers":
            numbers = rest[0]
        elif kind == "field":
            fields.append((caps(rest[0]), int(rest[1]), "hatch" in rest[2:]))
    cw, rh = 6.0 / width, 0.34                      # inches a bit, a row
    pieces, pos = [], 0                             # (row, first bit, bits, name, hatch)
    for name, n, hatch in fields:
        while n:
            take = min(n, width - pos % width)
            pieces.append((pos // width, pos % width, take, name, hatch))
            pos += take
            n -= take
    rows = (pos + width - 1) // width
    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=(6.0 + 0.6, rows * rh + 0.3))
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
        ax.set_xlim(-0.5, 6.1); ax.set_ylim(-rows * rh - 0.05, 0.25)
        for b in range(width):
            label = width - 1 - b if numbers == "down" else b
            ax.text((b + 0.5) * cw, 0.04, str(label), fontsize=4.6, ha="center", va="bottom")
            ax.plot([b * cw] * 2, [0, -0.04], color=INK, lw=0.4)
        for r in range(rows):
            ax.text(-0.08, -(r + 0.5) * rh, f"+{r * width // 8}", fontsize=5.2, ha="right", va="center")
        for r, b0, n, name, hatch in pieces:
            x, y = b0 * cw, -(r + 1) * rh
            ax.add_patch(Rectangle((x, y), n * cw, rh, fc="white", ec=INK, lw=0.8, hatch="//////" if hatch else None))
            for k in range(1, n):                    # bit ticks along the top of a field
                ax.plot([x + k * cw] * 2, [y + rh, y + rh - 0.035], color=INK, lw=0.35)
            narrow = n * cw < len(name) * 0.055
            ax.text(x + n * cw / 2, y + rh / 2, name, fontsize=4.4 if narrow else 5.8, ha="center", va="center",
                    rotation=90 if narrow and n * cw < 0.25 else 0,
                    bbox=dict(fc="white", ec="none", pad=0.4) if hatch else None)
        return svg(fig)


# -- categorical bars ------------------------------------------------------------------------------------------------

def bars(spec):
    """series "A" ["B" ...]          (one name a value column; series are told apart by hatch, keyed above)
       bar "CATEGORY" V [V ...]      (one line a category, in order)
       unit "LABEL"                  (the value axis)
       stacked                       (stack the series instead of setting them side by side)
       percent                       (stack each category as shares of its own total, 0 to 100)
       dots                          (a dot on a thin stem instead of a bar: a dot plot, lighter for many categories)
       horizontal                    (categories down the left, values across: for long names)
       log                           (a log value axis)
       size W H                      (inches; default 3.4 by 2.2)"""
    series, cats, unit, stacked, horiz, log, size, percent, dots = [], [], "", False, False, False, (3.4, 2.2), False, False
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "series":
            series = [caps(r) for r in rest]
        elif kind == "bar":
            cats.append((caps(rest[0]), [float(v) for v in rest[1:]]))
        elif kind == "unit":
            unit = caps(rest[0])
        elif kind == "stacked":
            stacked = True
        elif kind == "percent":
            stacked = percent = True
        elif kind == "dots":
            dots = True
        elif kind == "horizontal":
            horiz = True
        elif kind == "log":
            log = True
        elif kind == "size":
            size = (float(rest[0]), float(rest[1]))
    if percent:
        cats = [(c, [100 * v / (sum(vals) or 1) for v in vals]) for c, vals in cats]
    ns = max(len(v) for _, v in cats)
    fills = [("white", "//////"), ("white", None), (INK, None), ("white", "xxxx"), ("white", "....")]
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=size)
        width = 0.7 if stacked else 0.75 / ns
        for i, (_, vals) in enumerate(cats):
            base = 0.0
            for j, v in enumerate(vals):
                pos = i if stacked else i - 0.375 + width * (j + 0.5)
                fc, hatch = fills[j % len(fills)]
                kw = dict(color=fc, edgecolor=INK, linewidth=0.7, hatch=hatch)
                if dots and not stacked:
                    marker = "osD^v"[j % 5]
                    a, b = ([base, v], [-pos, -pos]) if horiz else ([pos, pos], [base, v])
                    ax.plot(a, b, color=INK, lw=0.5)
                    ax.plot([v] if horiz else [pos], [-pos] if horiz else [v], marker=marker,
                            ms=3.6, mfc=INK if j == 0 else "white", mec=INK, mew=0.7, ls="none")
                    _endlabel(ax, f"{v:g}", v, -pos if horiz else pos, horiz)
                    continue
                if horiz:
                    ax.barh(-pos, v, width, left=base, **kw)
                else:
                    ax.bar(pos, v, width, bottom=base, **kw)
                if not stacked:
                    _endlabel(ax, f"{v:g}", v, -pos if horiz else pos, horiz)
                elif percent and v >= 8:             # a share lettered inside its own segment
                    xy = (base + v / 2, -pos) if horiz else (pos, base + v / 2)
                    ax.text(*xy, f"{v:.0f} %", fontsize=5.2, ha="center", va="center",
                            color="white" if fc == INK else INK,
                            bbox=None if not hatch else dict(fc="white", ec="none", pad=0.5))
                base += v if stacked else 0
            if stacked and not percent:
                _endlabel(ax, f"{base:g}", base, -i if horiz else i, horiz)
        names = [c for c, _ in cats]
        if horiz:
            ax.set_yticks([-i for i in range(len(cats))], names); ax.tick_params(axis="y", length=0)
            ax.set_xlabel(unit, fontsize=6)
            if log:
                ax.set_xscale("log")
            ax.grid(True, axis="x", color=INK, lw=0.25, alpha=0.35)
            ax.margins(x=0.12)
        else:
            ax.set_xticks(range(len(cats)), names); ax.tick_params(axis="x", length=0)
            ax.set_ylabel(unit, fontsize=6)
            if log:
                ax.set_yscale("log")
            ax.grid(True, axis="y", color=INK, lw=0.25, alpha=0.35)
            ax.margins(y=0.1)
        ax.set_axisbelow(True)
        if len(series) > 1:                          # a key, only where series must be told apart
            for j, name in enumerate(series):
                fc, hatch = fills[j % len(fills)]
                if dots:
                    ax.plot([j / len(series) + 0.017], [1.065], marker="osD^v"[j % 5], ms=3.4, transform=ax.transAxes,
                            mfc=INK if j == 0 else "white", mec=INK, clip_on=False)
                    ax.text(j / len(series) + 0.05, 1.065, name, transform=ax.transAxes, fontsize=5.4, va="center")
                    continue
                x = j / len(series)
                ax.add_patch(Rectangle((x, 1.04), 0.035, 0.05, transform=ax.transAxes, fc=fc, ec=INK, lw=0.6,
                                       hatch=hatch, clip_on=False))
                ax.text(x + 0.05, 1.065, name, transform=ax.transAxes, fontsize=5.4, va="center")
        return svg(fig)


def _endlabel(ax, text, v, at, horiz):
    """a value just past the end of its bar"""
    xy, off = ((v, at), (3, 0)) if horiz else ((at, v), (0, 2))
    ax.annotate(text, xy=xy, xytext=off, textcoords="offset points", fontsize=5.6,
                ha="left" if horiz else "center", va="center" if horiz else "bottom")


# -- matrix ----------------------------------------------------------------------------------------------------------

def matrix(spec):
    """cols "A" "B" ...              (column heads, set slanted)
       row "NAME" V V ...            (one cell a column: yes, part, no, - for not applicable, a number, or short text)
       scale MAX                     (numbers are dots whose area is V / MAX of a full cell; default the largest)
       shade                         (numbers as a heatmap instead: each cell tinted by V / MAX, its value lettered)
     yes, part and no print as a full, half and open dot, the handbook's way of comparing at a glance"""
    cols, rows, scale, shade = [], [], None, False
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "cols":
            cols = [caps(c) for c in rest]
        elif kind == "row":
            rows.append((caps(rest[0]), rest[1:]))
        elif kind == "scale":
            scale = float(rest[0])
        elif kind == "shade":
            shade = True
    nums = [float(v) for _, vs in rows for v in vs if _isnum(v)]
    scale = scale or (max(nums) if nums else 1) or 1
    cw, rh, left = 0.42, 0.24, 1.6
    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=(left + cw * len(cols) + 0.3, rh * len(rows) + 0.75))
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
        ax.set_xlim(-left, cw * len(cols) + 0.3); ax.set_ylim(-rh * len(rows) - 0.05, 0.7)
        for j, c in enumerate(cols):
            ax.text((j + 0.5) * cw, 0.04, c, fontsize=5.6, rotation=40, ha="left", va="bottom", rotation_mode="anchor")
        for i, (name, vals) in enumerate(rows):
            yc = -(i + 0.5) * rh
            ax.text(-0.08, yc, name, fontsize=6, ha="right", va="center")
            ax.plot([-left + 0.1, cw * len(cols)], [-(i + 1) * rh] * 2, color=INK, lw=0.3, alpha=0.5)
            for j, v in enumerate(vals):
                xc, r = (j + 0.5) * cw, rh * 0.32
                lv = v.lower()
                if lv == "yes":
                    ax.add_patch(Circle((xc, yc), r, fc=INK, ec=INK, lw=0.7))
                elif lv == "no":
                    ax.add_patch(Circle((xc, yc), r, fc="white", ec=INK, lw=0.7))
                elif lv == "part":
                    ax.add_patch(Circle((xc, yc), r, fc="white", ec=INK, lw=0.7))
                    ax.add_patch(matplotlib.patches.Wedge((xc, yc), r, 90, 270, fc=INK, ec=INK, lw=0.7))
                elif lv == "-":
                    ax.plot([xc - r * 0.6, xc + r * 0.6], [yc, yc], color=INK, lw=0.7)
                elif _isnum(v) and shade:
                    f = min(float(v) / scale, 1)
                    ax.add_patch(Rectangle((j * cw + 0.01, -(i + 1) * rh + 0.01), cw - 0.02, rh - 0.02,
                                           fc=str(1 - 0.85 * f), ec="none"))
                    ax.text(xc, yc, f"{float(v):g}" if float(v) else "", fontsize=5.4, ha="center", va="center",
                            color="white" if f > 0.55 else INK)
                elif _isnum(v):
                    ax.add_patch(Circle((xc, yc), rh * 0.42 * (float(v) / scale) ** 0.5, fc=INK, ec=INK, lw=0.5))
                else:
                    ax.text(xc, yc, v.upper(), fontsize=5.4, ha="center", va="center")
        ax.plot([0, cw * len(cols)], [0, 0], color=INK, lw=0.8)
        return svg(fig)


def _isnum(v):
    try:
        float(v)
        return True
    except ValueError:
        return False


# -- tree ------------------------------------------------------------------------------------------------------------

def tree(spec):
    """an indented outline, two spaces a level, one node a line:
         DEPLOYMENT
           REPLICASET
             POD [dash]
       a trailing [dash] or [round] sets the box; the root is at the left and each level a column to the right
       ("down" alone on the first line sets the root at the top instead)"""
    lines = [l for l in spec.splitlines() if l.strip() and not l.strip().startswith("#")]
    down = lines and lines[0].strip() == "down"
    if down:
        lines = lines[1:]
    items = []                                       # (depth, label, shape)
    for l in lines:
        depth = (len(l) - len(l.lstrip(" "))) // 2
        text = l.strip()
        shape = "box"
        for s in ("dash", "round"):
            if text.endswith(f"[{s}]"):
                shape, text = s, text[: -len(s) - 2].strip()
        items.append((depth, caps(text.strip('"')), shape))
    base = min(d for d, _, _ in items)
    kids, parent, stackp = {i: [] for i in range(len(items))}, {}, []
    for i, (d, _, _) in enumerate(items):
        while stackp and items[stackp[-1]][0] >= d:
            stackp.pop()
        if stackp:
            parent[i] = stackp[-1]
            kids[stackp[-1]].append(i)
        stackp.append(i)
    slot, pos = [0], {}

    def place(i):                                    # leaves take the next slot, a parent the middle of its children
        if not kids[i]:
            pos[i] = slot[0]
            slot[0] += 1
        else:
            for k in kids[i]:
                place(k)
            pos[i] = (pos[kids[i][0]] + pos[kids[i][-1]]) / 2
    for i in range(len(items)):
        if i not in parent:
            place(i)
    bw, bh = 1.15, 0.36
    step_d, step_s = (0.75, 1.35) if down else (1.55, 0.48)
    xy = {i: ((pos[i] * step_s, -(items[i][0] - base) * step_d) if down else
              ((items[i][0] - base) * step_d, -pos[i] * step_s)) for i in pos}
    xs = [p[0] for p in xy.values()]; ys = [p[1] for p in xy.values()]
    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=(max(xs) - min(xs) + bw + 0.3, max(ys) - min(ys) + bh + 0.3))
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
        ax.set_xlim(min(xs) - bw / 2 - 0.15, max(xs) + bw / 2 + 0.15)
        ax.set_ylim(min(ys) - bh / 2 - 0.15, max(ys) + bh / 2 + 0.15)
        for i, ks in kids.items():
            if not ks:
                continue
            px, py = xy[i]
            if down:
                mid = py - step_d / 2
                ax.plot([px, px], [py - bh / 2, mid], color=INK, lw=0.7)
                ax.plot([xy[ks[0]][0], xy[ks[-1]][0]], [mid, mid], color=INK, lw=0.7)
                for k in ks:
                    ax.plot([xy[k][0]] * 2, [mid, xy[k][1] + bh / 2], color=INK, lw=0.7)
            else:
                mid = px + step_d / 2
                ax.plot([px + bw / 2, mid], [py, py], color=INK, lw=0.7)
                ax.plot([mid, mid], [xy[ks[0]][1], xy[ks[-1]][1]], color=INK, lw=0.7)
                for k in ks:
                    ax.plot([mid, xy[k][0] - bw / 2], [xy[k][1]] * 2, color=INK, lw=0.7)
        for i, (x, y) in xy.items():
            _, label, shape = items[i]
            ax.add_patch(FancyBboxPatch((x - bw / 2, y - bh / 2), bw, bh, fc="white", ec=INK, lw=0.9,
                                        boxstyle=f"round,pad=0,rounding_size={0.08 if shape == 'round' else 0}",
                                        ls=(0, (4, 2)) if shape == "dash" else "-"))
            ax.text(x, y, label, fontsize=5.8, ha="center", va="center", linespacing=1.05)
        return svg(fig)


# -- callouts on a picture -------------------------------------------------------------------------------------------

def callouts(spec, base=Path(".")):
    """image PATH [gray]             (a PNG, relative to the sheet; set in gray, gray inverts a dark screen to ink)
       at X Y "TEXT"                 (a leader from the point X, Y, fractions of the picture from its top left,
                                      to lettering in the margin on the nearer side)
       width W                       (inches of the picture; default 2.6)"""
    import matplotlib.image as mpimg
    path, invert, points, width = None, False, [], 2.6
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "image":
            path, invert = base / rest[0], "gray" in rest[1:]
        elif kind == "at":
            points.append((float(rest[0]), float(rest[1]), caps(rest[2])))
        elif kind == "width":
            width = float(rest[0])
    img = mpimg.imread(path)
    lum = img[..., :3] @ [0.299, 0.587, 0.114] if img.ndim == 3 else img
    if invert:
        lum = 1 - lum
    hgt = width * lum.shape[0] / lum.shape[1]
    margin, gap = 1.7, 0.17
    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=(width + 2 * margin, hgt + 0.2))
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
        ax.set_xlim(-margin, width + margin); ax.set_ylim(-0.1, hgt + 0.1)
        ax.imshow(lum, cmap="gray", vmin=0, vmax=1, extent=(0, width, 0, hgt), interpolation="lanczos")
        ax.add_patch(Rectangle((0, 0), width, hgt, fill=False, ec=INK, lw=0.6))
        for side in ("l", "r"):
            pts = sorted(((x * width, (1 - y) * hgt, text) for x, y, text in points if (x < 0.5) == (side == "l")),
                         key=lambda p: -p[1])
            ys, last = [], None
            for _, py, _ in pts:                     # keep the lettering at least a line apart, top down
                y = py if last is None else min(py, last - gap)
                ys.append(y)
                last = y
            lift = max(0.0, 0.05 - min(ys)) if ys else 0.0       # pushed off the bottom: lift the column
            ys = [y + lift for y in ys]
            for (px, py, text), y in zip(pts, ys):
                tx = -0.15 if side == "l" else width + 0.15
                ax.plot([px, tx], [py, y], color=INK, lw=0.6)
                ax.add_patch(Circle((px, py), 0.025, fc=INK, ec="white", lw=0.5))
                ax.text(tx + (-0.04 if side == "l" else 0.04), y, text, fontsize=5.6, va="center",
                        ha="right" if side == "l" else "left", linespacing=1.05)
        return svg(fig)


# -- scatter and bubbles ---------------------------------------------------------------------------------------------

def scatter(spec, base=Path(".")):
    """point X Y ["LABEL"] [size=N]   (one point a line; size= makes it a bubble, area by value)
       csv PATH X Y [size=COL] [label=COL]   (points from columns of a CSV instead)
       xlabel "LABEL" / ylabel "LABEL"
       log x|y|xy
       fit                            (a least-squares line, with r, on the axes as drawn: log axes fit the logs)
       size W H                       (inches; default 3.4 by 2.4)"""
    pts, xlabel, ylabel, log, fit, size = [], "", "", "", False, (3.4, 2.4)
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        opts = dict(o.split("=", 1) for o in rest if "=" in o)
        rest = [r for r in rest if "=" not in r]
        if kind == "point":
            pts.append((float(rest[0]), float(rest[1]), float(opts["size"]) if "size" in opts else None,
                        caps(rest[2]) if len(rest) > 2 else ""))
        elif kind == "csv":
            with open(base / rest[0], newline="") as fh:
                for row in csv.DictReader(fh):
                    pts.append((float(row[rest[1]]), float(row[rest[2]]),
                                float(row[opts["size"]]) if "size" in opts else None,
                                caps(row[opts["label"]]) if "label" in opts else ""))
        elif kind == "xlabel":
            xlabel = caps(rest[0])
        elif kind == "ylabel":
            ylabel = caps(rest[0])
        elif kind == "log":
            log = rest[0]
        elif kind == "fit":
            fit = True
        elif kind == "size":
            size = (float(rest[0]), float(rest[1]))
    big = max((p[2] for p in pts if p[2] is not None), default=None) or 1
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=size)
        for x, y, s, label in pts:
            area = 6 if s is None else 6 + 260 * s / big
            ax.scatter([x], [y], s=area, facecolor="white" if s is None else "#cfcfcf", edgecolor=INK, linewidth=0.7,
                       zorder=3)
            if label:
                ax.annotate(label, xy=(x, y), xytext=(5, 3), textcoords="offset points", fontsize=5.4, zorder=4,
                            bbox=dict(fc="white", ec="none", pad=0.3))      # over the fit line, not under it
        if "x" in log:
            ax.set_xscale("log")
        if "y" in log:
            ax.set_yscale("log")
        if fit and len(pts) > 2 and len({p[0] for p in pts}) > 1:
            fx = np.array([p[0] for p in pts]); fy = np.array([p[1] for p in pts])
            keep = ((fx > 0) | ("x" not in log)) & ((fy > 0) | ("y" not in log))     # a log axis fits positives
            fx, fy = fx[keep], fy[keep]
            tx = np.log10(fx) if "x" in log else fx
            ty = np.log10(fy) if "y" in log else fy
            m, c = np.polyfit(tx, ty, 1)
            r = np.corrcoef(tx, ty)[0, 1]
            gx = np.linspace(tx.min(), tx.max(), 50)
            gy = m * gx + c
            ax.plot(10 ** gx if "x" in log else gx, 10 ** gy if "y" in log else gy, color=INK, lw=0.7,
                    ls=(0, (5, 2)), zorder=2)
            ax.text(0.03, 0.95, f"LEAST SQUARES, R = {r:.2f}", transform=ax.transAxes, fontsize=5.4, va="top")
        ax.margins(0.12)
        ax.grid(True, color=INK, lw=0.25, alpha=0.35)
        ax.set_xlabel(xlabel, fontsize=6); ax.set_ylabel(ylabel, fontsize=6)
        return svg(fig)


# -- distributions ---------------------------------------------------------------------------------------------------

def dist(spec, base=Path(".")):
    """box "NAME" MIN Q1 MEDIAN Q3 MAX [OUTLIER ...]   (a box from its five numbers)
       data "NAME" PATH COLUMN [where=COL:VALUE]      (a box from raw values in a CSV: quartiles, whiskers to 1.5 IQR,
                                                       the rest as outliers)
       violin                                          (raw rows drawn as violins round their boxes)
       strip                                           (every raw value as a dot over its box)
       ecdf                                            (raw rows as cumulative curves instead of boxes: the share of
                                                        runs at or under each value, percentiles read off directly)
       hist PATH COLUMN [where=COL:VALUE] [bins=N]    (a histogram instead of boxes; one only)
       mark AT "LABEL"                                 (a dashed line across, a limit or a percentile)
       unit "LABEL"
       size W H                                        (inches; default 3.4 by 2.2)"""
    boxes, raw, marks, unit, violin, hist, size, strip, ecdf = [], [], [], "", False, None, (3.4, 2.2), False, False

    def column(path, col, opts):
        where = opts.get("where")
        key, _, want = where.partition(":") if where else ("", "", "")
        with open(base / path, newline="") as fh:
            return [float(r[col]) for r in csv.DictReader(fh) if not where or r[key] == want]
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        opts = dict(o.split("=", 1) for o in rest if "=" in o)
        rest = [r for r in rest if "=" not in r]
        if kind == "box":
            v = [float(x) for x in rest[1:]]
            boxes.append(dict(label=caps(rest[0]), whislo=v[0], q1=v[1], med=v[2], q3=v[3], whishi=v[4], fliers=v[5:]))
        elif kind == "data":
            vals = np.array(column(rest[1], rest[2], opts))
            q1, med, q3 = np.percentile(vals, [25, 50, 75])
            lo, hi = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
            inside = vals[(vals >= lo) & (vals <= hi)]
            boxes.append(dict(label=caps(rest[0]), whislo=inside.min(), q1=q1, med=med, q3=q3, whishi=inside.max(),
                              fliers=vals[(vals < lo) | (vals > hi)].tolist()))
            raw.append(vals)
        elif kind == "violin":
            violin = True
        elif kind == "strip":
            strip = True
        elif kind == "ecdf":
            ecdf = True
        elif kind == "hist":
            hist = (column(rest[0], rest[1], opts), int(opts.get("bins", 20)))
        elif kind == "mark":
            marks.append((float(rest[0]), caps(rest[1])))
        elif kind == "unit":
            unit = caps(rest[0])
        elif kind == "size":
            size = (float(rest[0]), float(rest[1]))
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=size)
        if ecdf and raw:
            for i, (b, vals) in enumerate(zip(boxes, raw)):
                v = np.sort(vals)
                ax.step(v, np.arange(1, len(v) + 1) / len(v) * 100, where="post", color=INK, lw=0.9,
                        ls=DASHES[i % len(DASHES)])
                ax.annotate(b["label"], xy=(v[-1], 100), xytext=(3, -4 - 7 * i), textcoords="offset points",
                            fontsize=5.4, annotation_clip=False)
            ax.set_xlabel(unit, fontsize=6); ax.set_ylabel("% AT OR UNDER", fontsize=6)
            for at, label in marks:
                ax.axvline(at, color=INK, lw=0.7, ls=(0, (3, 2)))
                ax.text(at, 1.0, label, fontsize=5.4, ha="center", va="bottom", transform=ax.get_xaxis_transform())
            ax.grid(True, color=INK, lw=0.25, alpha=0.35)
        elif hist:
            ax.hist(hist[0], bins=hist[1], color="white", edgecolor=INK, linewidth=0.7, hatch="//////")
            ax.set_xlabel(unit, fontsize=6); ax.set_ylabel("COUNT", fontsize=6)
            for at, label in marks:
                ax.axvline(at, color=INK, lw=0.7, ls=(0, (3, 2)))
                ax.text(at, 1.0, label, fontsize=5.4, ha="center", va="bottom", transform=ax.get_xaxis_transform())
            ax.grid(True, axis="y", color=INK, lw=0.25, alpha=0.35)
        else:
            pos = list(range(len(boxes), 0, -1))
            if violin and raw and len(raw) == len(boxes):
                parts = ax.violinplot(raw, positions=pos, vert=False, showextrema=False, widths=0.8)
                for b in parts["bodies"]:
                    b.set_facecolor("#e2e2e2"); b.set_edgecolor(INK); b.set_linewidth(0.5); b.set_alpha(1)
            ax.bxp(boxes, positions=pos, vert=False, widths=0.32 if violin else 0.5, patch_artist=True,
                   boxprops=dict(facecolor="white", edgecolor=INK, linewidth=0.8),
                   medianprops=dict(color=INK, linewidth=1.6), whiskerprops=dict(color=INK, linewidth=0.7),
                   capprops=dict(color=INK, linewidth=0.7),
                   flierprops=dict(marker="o", markersize=2.4, markerfacecolor="white", markeredgecolor=INK))
            if strip and raw and len(raw) == len(boxes):
                rng = np.random.default_rng(0)                   # the same jitter every render
                for p_, vals in zip(pos, raw):
                    ax.plot(vals, p_ + rng.uniform(-0.12, 0.12, len(vals)), ls="none", marker="o", ms=1.6,
                            mfc="white", mec=INK, mew=0.4, zorder=3)
            ax.set_yticks(pos, [b["label"] for b in boxes]); ax.tick_params(axis="y", length=0)
            ax.set_xlabel(unit, fontsize=6)
            for at, label in marks:
                ax.axvline(at, color=INK, lw=0.7, ls=(0, (3, 2)))
                ax.text(at, 1.0, label, fontsize=5.4, ha="center", va="bottom", transform=ax.get_xaxis_transform())
            ax.grid(True, axis="x", color=INK, lw=0.25, alpha=0.35)
            ax.spines["left"].set_visible(False)
        ax.set_axisbelow(True)
        return svg(fig)


# -- sankey ----------------------------------------------------------------------------------------------------------

def sankey(spec):
    """flow "FROM" "TO" VALUE        (one line a flow; columns follow from the flows, sources at the left)
       unit "LABEL"                   (printed after each node's total)
       size W H                       (inches between the first and last columns; default 4.2 by 2.6)
     ribbon width is proportional to value; a node's height is the larger of what comes in and what goes out"""
    flows, unit, size = [], "", (4.2, 2.6)
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "flow":
            flows.append((caps(rest[0]), caps(rest[1]), float(rest[2])))
        elif kind == "unit":
            unit = rest[0]
        elif kind == "size":
            size = (float(rest[0]), float(rest[1]))
    flows = [f for f in flows if f[2] > 0]
    if not flows:
        raise SystemExit("handbook: sankey has no flows above zero")
    names = list(dict.fromkeys([a for a, _, _ in flows] + [b for _, b, _ in flows]))
    col = {n: 0 for n in names}
    for _ in names:                                  # longest path from a source sets the column
        for a, b, _ in flows:
            col[b] = max(col[b], col[a] + 1)
    if any(col[b] <= col[a] for a, b, _ in flows):
        raise SystemExit("handbook: sankey flows run in a circle; a sankey must flow one way")
    inflow = {n: sum(v for _, b, v in flows if b == n) for n in names}
    outflow = {n: sum(v for a, _, v in flows if a == n) for n in names}
    val = {n: max(inflow[n], outflow[n]) for n in names}
    ncol = max(col.values()) + 1
    W, H = size
    gap, nw = 0.12, 0.07
    cols = [[n for n in names if col[n] == c] for c in range(ncol)]
    k = min((H - gap * (len(c) - 1)) / sum(val[n] for n in c) for c in cols)   # inches per unit
    top, xs = {}, {}
    for c, members in enumerate(cols):
        y = H - (H - sum(val[n] * k for n in members) - gap * (len(members) - 1)) / 2
        for n in members:
            top[n], xs[n] = y, c * (W - nw) / max(ncol - 1, 1)
            y -= val[n] * k + gap
    from matplotlib.path import Path as MPath
    out_off = {n: 0.0 for n in names}
    in_off = {n: 0.0 for n in names}
    order = sorted(flows, key=lambda f: (-top[f[0]], -top[f[1]]))
    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=(W + 2.4, H + 0.3))
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
        ax.set_xlim(-1.2, W + 1.2); ax.set_ylim(-0.15, H + 0.15)
        for a, b, v in order:
            h = v * k
            y0 = top[a] - out_off[a]; out_off[a] += h
            y1 = top[b] - in_off[b]; in_off[b] += h
            x0, x1 = xs[a] + nw, xs[b]
            m = (x0 + x1) / 2
            verts = [(x0, y0), (m, y0), (m, y1), (x1, y1), (x1, y1 - h), (m, y1 - h), (m, y0 - h), (x0, y0 - h),
                     (x0, y0)]
            codes = [MPath.MOVETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4, MPath.LINETO, MPath.CURVE4,
                     MPath.CURVE4, MPath.CURVE4, MPath.CLOSEPOLY]
            ax.add_patch(matplotlib.patches.PathPatch(MPath(verts, codes), fc="#d4d4d4", ec=INK, lw=0.35, alpha=0.9))
        for n in names:
            ax.add_patch(Rectangle((xs[n], top[n] - val[n] * k), nw, val[n] * k, fc=INK, ec=INK, lw=0.5))
            left = col[n] == 0
            ax.text(xs[n] - 0.05 if left else xs[n] + nw + 0.05, top[n] - val[n] * k / 2,
                    f"{n}\n{val[n]:g} {unit}".rstrip(), fontsize=5.6, va="center", linespacing=1.1,
                    ha="right" if left else "left")
        return svg(fig)


# -- treemap ---------------------------------------------------------------------------------------------------------

def treemap(spec):
    """an indented outline, two spaces a level; a leaf ends in its value, a parent is the sum of its children:
         SHEETS
           PDF 2255
           PY 79
       size W H                       (inches, on a line of its own; default 6.2 by 3)
     the first level are framed heavy and named in their corner; a leaf is lettered with its value when it has
     room, by name alone when only that fits, and left blank below that (its value is still in the source)"""
    size, items = (6.2, 3.0), []
    for l in spec.splitlines():
        if not l.strip() or l.strip().startswith("#"):
            continue
        if l.strip().startswith("size "):
            size = tuple(float(v) for v in l.split()[1:3])
            continue
        depth = (len(l) - len(l.lstrip(" "))) // 2
        m = re.fullmatch(r"(.*?)\s+(-?[\d.]+)", l.strip())     # a name, then its value if it ends in one
        name, value = (m.group(1), float(m.group(2))) if m else (l.strip(), 0.0)
        items.append([depth, caps(name.strip().strip('"')), value, []])
    roots, stackp = [], []
    for it in items:
        while stackp and stackp[-1][0] >= it[0]:
            stackp.pop()
        (stackp[-1][3] if stackp else roots).append(it)
        stackp.append(it)

    def total(it):
        return it[2] if not it[3] else sum(total(k) for k in it[3])

    def prune(group):                                # nothing of size 0 takes up room
        for it in group:
            it[3] = prune(it[3])
        return [it for it in group if total(it) > 0]
    roots = prune(roots)
    if not roots:
        raise SystemExit("handbook: treemap has nothing above zero")

    def squarify(group, x, y, w, h):
        """lay a list of items into a rectangle by rows of near-square cells"""
        group = sorted(group, key=total, reverse=True)
        out, scale = [], w * h / sum(total(g) for g in group)
        while group:
            short = min(w, h)
            row, best = [], float("inf")
            for g in group:
                trial = row + [g]
                s = sum(total(t) for t in trial) * scale
                worst = max(max(short ** 2 * total(t) * scale / s ** 2, s ** 2 / (short ** 2 * total(t) * scale))
                            for t in trial)
                if worst > best:
                    break
                row, best = trial, worst
            group = group[len(row):]
            s = sum(total(t) for t in row) * scale
            if w >= h:                                # the row stands as a column at the left
                cw, cy = s / h, y
                for t in row:
                    ch = total(t) * scale / cw
                    out.append((t, x, cy, cw, ch)); cy += ch
                x, w = x + cw, w - cw
            else:
                rh, cx = s / w, x
                for t in row:
                    c = total(t) * scale / rh
                    out.append((t, cx, y, c, rh)); cx += c
                y, h = y + rh, h - rh
        return out
    W, H = size
    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=(W + 0.1, H + 0.1))
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
        ax.set_xlim(-0.05, W + 0.05); ax.set_ylim(H + 0.05, -0.05)        # y runs down, as the eye reads

        def draw(group, x, y, w, h, depth):
            for it, cx, cy, cw, ch in squarify(group, x, y, w, h):
                pad = 0.03 if depth else 0.0
                ax.add_patch(Rectangle((cx + pad, cy + pad), cw - 2 * pad, ch - 2 * pad, fill=False, ec=INK,
                                       lw=1.4 if depth == 0 else 0.6))
                if it[3]:
                    head = f"{it[1]}  {total(it):g}"
                    if cw < len(head) * 0.055:              # a narrow group keeps its name, drops its total
                        head = it[1] if cw >= len(it[1]) * 0.055 else ""
                    ax.text(cx + 0.05, cy + 0.04, head, fontsize=5.8, va="top", ha="left", fontweight="bold")
                    draw(it[3], cx + 0.03, cy + 0.17, cw - 0.06, ch - 0.2, depth + 1)
                elif cw > 0.32 and ch > 0.16:
                    ax.text(cx + cw / 2, cy + ch / 2, f"{it[1]}\n{total(it):g}", fontsize=5.2 if cw > 0.5 else 4.4,
                            ha="center", va="center", linespacing=1.05)
                elif max(cw, ch) > len(it[1]) * 0.045 + 0.04 and min(cw, ch) > 0.07:   # the name alone, along it
                    ax.text(cx + cw / 2, cy + ch / 2, it[1], fontsize=4.2, ha="center", va="center",
                            rotation=90 if ch > cw else 0)
        draw(roots, 0, 0, W, H, 0)
        return svg(fig)


# -- quadrant --------------------------------------------------------------------------------------------------------

def quadrant(spec):
    """x "LOW" "HIGH"                  (the axis, its two ends lettered)
       y "LOW" "HIGH"
       name 1|2|3|4 "TEXT"             (a quadrant's name: 1 top right, 2 top left, 3 bottom left, 4 bottom right)
       point X Y "LABEL"               (X and Y from 0 to 1)"""
    xl, yl, names, pts = ("", ""), ("", ""), {}, []
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "x":
            xl = (caps(rest[0]), caps(rest[1]))
        elif kind == "y":
            yl = (caps(rest[0]), caps(rest[1]))
        elif kind == "name":
            names[int(rest[0])] = caps(rest[1])
        elif kind == "point":
            pts.append((float(rest[0]), float(rest[1]), caps(rest[2])))
    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=(3.6, 3.2))
        ax = fig.add_axes([0.1, 0.08, 0.85, 0.88]); ax.set_axis_off()
        ax.set_xlim(-0.02, 1.02); ax.set_ylim(-0.02, 1.02)
        ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, ec=INK, lw=1.0))
        ax.plot([0.5, 0.5], [0, 1], color=INK, lw=0.6); ax.plot([0, 1], [0.5, 0.5], color=INK, lw=0.6)
        for q, (x, y, ha) in {1: (0.97, 0.97, "right"), 2: (0.03, 0.97, "left"), 3: (0.03, 0.03, "left"),
                              4: (0.97, 0.03, "right")}.items():
            if q in names:
                ax.text(x, y, names[q], fontsize=6.2, fontweight="bold", ha=ha, va="top" if y > 0.5 else "bottom")
        for x, y, label in pts:
            ax.plot([x], [y], marker="o", ms=3.2, mfc=INK, mec=INK)
            right = x > 0.7                          # lettering to the left near the right edge
            ax.annotate(label, xy=(x, y), xytext=(-4 if right else 4, 2), textcoords="offset points", fontsize=5.4,
                        ha="right" if right else "left")
        ax.text(0, -0.03, xl[0], fontsize=5.6, ha="left", va="top"); ax.text(1, -0.03, xl[1], fontsize=5.6, ha="right", va="top")
        ax.text(-0.03, 0, yl[0], fontsize=5.6, ha="right", va="bottom", rotation=90)
        ax.text(-0.03, 1, yl[1], fontsize=5.6, ha="right", va="top", rotation=90)
        return svg(fig)


# -- venn ------------------------------------------------------------------------------------------------------------

def venn(spec):
    """set "A" "B" ["C"]               (two or three sets, named)
       in REGION "TEXT"                (REGION: A, B, C, AB, AC, BC, ABC, or out for none of them)"""
    sets, regions = [], {}
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "set":
            sets = [caps(s) for s in rest]
        elif kind == "in":
            key = rest[0].upper()
            regions[key if key == "OUT" else "".join(sorted(key))] = caps(rest[1])     # BA is AB
    three = len(sets) == 3
    r = 1.0
    centres = [(-0.55, 0.3), (0.55, 0.3), (0, -0.62)] if three else [(-0.6, 0), (0.6, 0)]
    spots = ({"A": (-0.95, 0.55), "B": (0.95, 0.55), "C": (0, -1.15), "AB": (0, 0.72), "AC": (-0.72, -0.4),
              "BC": (0.72, -0.4), "ABC": (0, 0.0), "OUT": (1.65, -1.45)} if three else
             {"A": (-1.0, 0), "B": (1.0, 0), "AB": (0, 0), "OUT": (1.75, -1.0)})
    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=(4.4, 3.0 if three else 2.1))
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off(); ax.set_aspect("equal")
        ax.set_xlim(-2.9, 2.9); ax.set_ylim(-1.75, 1.6) if three else ax.set_ylim(-1.25, 1.35)
        for (cx, cy), name, ls in zip(centres, sets, ["-", (0, (5, 2)), (0, (1.5, 1.5))]):
            ax.add_patch(Circle((cx, cy), r, fill=False, ec=INK, lw=0.9, ls=ls))
        heads = [(-1.55, 1.4, "right"), (1.55, 1.4, "left"), (-1.0, -1.55, "right")] if three else \
                [(-1.65, 0.9, "right"), (1.65, 0.9, "left")]
        for (hx, hy, ha), name in zip(heads, sets):           # outside the circles, clear of their lines
            ax.text(hx, hy, name, fontsize=6.4, fontweight="bold", ha=ha, va="center")
        for key, text in regions.items():
            x, y = spots[key]
            ax.text(x, y, text, fontsize=5.4, ha="center", va="center", linespacing=1.1)
        return svg(fig)


# -- funnel ----------------------------------------------------------------------------------------------------------

def funnel(spec):
    """stage "NAME" VALUE             (top to bottom; each printed with its share of the first stage)
       unit "LABEL" """
    stages, unit = [], ""
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "stage":
            stages.append((caps(rest[0]), float(rest[1])))
        elif kind == "unit":
            unit = rest[0]
    top = stages[0][1]
    if top <= 0:
        raise SystemExit("handbook: funnel's first stage must be above zero")
    W, rh = 3.2, 0.34
    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=(W + 3.0, rh * len(stages) + 0.2))
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
        ax.set_xlim(-1.4, W + 1.6); ax.set_ylim(-rh * len(stages) - 0.05, 0.15)
        for i, (name, v) in enumerate(stages):
            w0 = W * v / top
            w1 = W * stages[i + 1][1] / top if i + 1 < len(stages) else w0
            y0, y1 = -i * rh, -(i + 1) * rh + 0.04
            ax.add_patch(plt.Polygon([(W / 2 - w0 / 2, y0), (W / 2 + w0 / 2, y0), (W / 2 + w1 / 2, y1),
                                      (W / 2 - w1 / 2, y1)], closed=True, fc="white", ec=INK, lw=0.8,
                                     hatch="//////" if i % 2 else None))
            ax.text(-0.1, (y0 + y1) / 2, name, fontsize=6, ha="right", va="center")
            ax.text(W + 0.1, (y0 + y1) / 2, f"{v:g} {unit},  {100 * v / top:.0f} %",
                    fontsize=5.8, ha="left", va="center")
        return svg(fig)


# -- waterfall -------------------------------------------------------------------------------------------------------

def waterfall(spec):
    """start "LABEL" V               (the opening total, a full bar)
       step "LABEL" +V | -V          (a rise or a fall from the running total, hatched for a fall)
       total "LABEL"                 (the running total so far, a full bar)
       unit "LABEL"
       size W H                      (inches; default 4.4 by 2.4)"""
    items, unit, size = [], "", (4.4, 2.4)
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind in ("start", "step"):
            items.append((kind, caps(rest[0]), float(rest[1])))
        elif kind == "total":
            items.append((kind, caps(rest[0]), None))
        elif kind == "unit":
            unit = caps(rest[0])
        elif kind == "size":
            size = (float(rest[0]), float(rest[1]))
    if not items:
        raise SystemExit("handbook: waterfall has no steps")
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=size)
        run, prev_top = 0.0, None
        for i, (kind, label, v) in enumerate(items):
            if kind == "step":
                lo, hi = sorted((run, run + v))
                ax.bar(i, hi - lo, 0.62, bottom=lo, color="white", edgecolor=INK, linewidth=0.7,
                       hatch="//////" if v < 0 else None)
                run += v
                ax.annotate(f"{v:+g}", xy=(i, hi), xytext=(0, 2), textcoords="offset points", fontsize=5.4,
                            ha="center", va="bottom")
            else:
                run = v if kind == "start" else run
                ax.bar(i, run, 0.62, color=INK, edgecolor=INK, linewidth=0.7)
                ax.annotate(f"{run:g}", xy=(i, max(run, 0)), xytext=(0, 2), textcoords="offset points",
                            fontsize=5.4, ha="center", va="bottom")
            if prev_top is not None:                      # a thin rule carries the total across
                ax.plot([i - 1 + 0.31, i - 0.31], [prev_top, prev_top], color=INK, lw=0.5, ls=(0, (2, 1.5)))
            prev_top = run
        ax.set_xticks(range(len(items)), [l for _, l, _ in items]); ax.tick_params(axis="x", length=0)
        ax.axhline(0, color=INK, lw=0.6)
        ax.set_ylabel(unit, fontsize=6)
        ax.grid(True, axis="y", color=INK, lw=0.25, alpha=0.35); ax.set_axisbelow(True)
        ax.margins(y=0.12)
        return svg(fig)


# -- waffle ----------------------------------------------------------------------------------------------------------

def waffle(spec):
    """part "LABEL" V                (shares of a whole on a 10 by 10 grid, one square a percent, in order)
       cells N                       (squares a side; default 10)"""
    parts, n = [], 10
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "part":
            parts.append((caps(rest[0]), float(rest[1])))
        elif kind == "cells":
            n = int(rest[0])
    total = sum(v for _, v in parts)
    if total <= 0:
        raise SystemExit("handbook: waffle has nothing above zero")
    counts = [round(v / total * n * n) for _, v in parts]
    counts[-1] += n * n - sum(counts)                    # rounding settles on the last part
    fills = [(INK, None), ("white", "//////"), ("white", "xxxx"), ("white", "...."), ("white", None)]
    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=(4.4, 2.2))
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off(); ax.set_aspect("equal")
        c = 1.9 / n
        k = 0
        for j, cnt in enumerate(counts):
            fc, hatch = fills[j % len(fills)]
            for _ in range(cnt):
                col, row = divmod(k, n)                  # fill column by column, top to bottom
                ax.add_patch(Rectangle((col * c, -(row + 1) * c), c * 0.86, c * 0.86, fc=fc, ec=INK, lw=0.4,
                                       hatch=hatch))
                k += 1
            ax.add_patch(Rectangle((2.15, -0.2 - j * 0.26), 0.14, 0.14, fc=fc, ec=INK, lw=0.5, hatch=hatch))
            ax.text(2.36, -0.13 - j * 0.26, f"{parts[j][0]}  {100 * parts[j][1] / total:.0f} %", fontsize=6,
                    va="center")
        ax.set_xlim(-0.05, 4.3); ax.set_ylim(-2.0, 0.05)
        return svg(fig)


# -- slope -----------------------------------------------------------------------------------------------------------

def slope(spec):
    """heads "BEFORE" "AFTER"        (the two columns' names: two dates, two builds, two conditions)
       item "NAME" A B               (one line a thing; it runs from A to B, lettered at both ends)
       unit "LABEL"
       log"""
    heads, items, unit, log = ("", ""), [], "", False
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "heads":
            heads = (caps(rest[0]), caps(rest[1]))
        elif kind == "item":
            items.append((caps(rest[0]), float(rest[1]), float(rest[2])))
        elif kind == "unit":
            unit = caps(rest[0])
        elif kind == "log":
            log = True
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(3.6, 2.8))
        for i, (name, a, b) in enumerate(items):
            ax.plot([0, 1], [a, b], color=INK, lw=0.8, ls=DASHES[i % len(DASHES)], marker="o", ms=2.8, mfc="white")
            ax.annotate(f"{name}  {a:g}", xy=(0, a), xytext=(-5, 0), textcoords="offset points", fontsize=5.4,
                        ha="right", va="center")
            ax.annotate(f"{b:g}  {name}", xy=(1, b), xytext=(5, 0), textcoords="offset points", fontsize=5.4,
                        ha="left", va="center")
        if log:
            ax.set_yscale("log")
        ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
        ax.set_xlim(-0.05, 1.05); ax.set_xticks([0, 1], heads); ax.tick_params(axis="x", length=0)
        ax.set_yticks([]); ax.spines["left"].set_visible(False)
        for x in (0, 1):
            ax.axvline(x, color=INK, lw=0.5)
        ax.set_ylabel(unit, fontsize=6)
        return svg(fig)


# -- parallel coordinates --------------------------------------------------------------------------------------------

def parallel(spec, base=Path(".")):
    """axes "A" "B" "C" ...          (one vertical axis a quantity, left to right, each scaled to its own range)
       item "NAME" VA VB VC ...       (one line a thing, across every axis)
       csv PATH NAMECOL COL COL ...   (items from a CSV instead)"""
    axes, items = [], []
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "axes":
            axes = [caps(a) for a in rest]
        elif kind == "item":
            items.append((caps(rest[0]), [float(v) for v in rest[1:]]))
        elif kind == "csv":
            with open(base / rest[0], newline="") as fh:
                for row in csv.DictReader(fh):
                    items.append((caps(row[rest[1]]), [float(row[c]) for c in rest[2:]]))
            axes = axes or [caps(c) for c in rest[2:]]
    data = np.array([v for _, v in items], dtype=float)
    lo, hi = data.min(axis=0), data.max(axis=0)
    span = np.where(hi > lo, hi - lo, 1)
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(max(3.4, 1.1 * len(axes)), 2.4))
        ends = []
        for i, (name, v) in enumerate(items):
            y = (np.asarray(v) - lo) / span
            ax.plot(range(len(axes)), y, color=INK, lw=0.8, ls=DASHES[i % len(DASHES)], marker="o", ms=2.2,
                    mfc="white")
            ends.append((y[-1], name))
        for (y, name), ly in zip(sorted(ends), _spread([e[0] for e in sorted(ends)], 0.08)):
            ax.annotate(name, xy=(len(axes) - 1, y), xytext=(len(axes) - 1 + 0.12, ly), fontsize=5.4, va="center",
                        annotation_clip=False, arrowprops=dict(arrowstyle="-", color=INK, lw=0.4) if abs(ly - y) > 0.01
                        else None)
        for j, a in enumerate(axes):
            ax.axvline(j, color=INK, lw=0.7)
            ax.text(j, -0.08, f"{lo[j]:g}", fontsize=5, ha="center", va="top")
            ax.text(j, 1.06, f"{hi[j]:g}", fontsize=5, ha="center", va="bottom")
        ax.set_xticks(range(len(axes)), axes); ax.tick_params(axis="x", length=0, pad=10)
        ax.set_yticks([]); ax.spines["left"].set_visible(False); ax.spines["bottom"].set_visible(False)
        ax.set_ylim(-0.12, 1.1)
        return svg(fig)


def _spread(ys, gap):
    """ys, sorted ascending, moved apart to at least gap, the run kept centred on where it was"""
    out = []
    for y in ys:
        out.append(max(y, out[-1] + gap) if out else y)
    shift = (sum(ys) - sum(out)) / len(out) if out else 0
    return [y + shift for y in out]


# -- network ---------------------------------------------------------------------------------------------------------

def network(spec):
    """node ID "LABEL" [box|round|dash|drum]   (optional: a node needs no line of its own unless it wants a label)
       link A B ["LABEL"] [dash] [arrow]       (an edge; arrow for a direction)
       layout spring|circle                    (spring, the default, pulls linked nodes together)
       size W H                                (inches; default 5 by 3)
     for graphs with no natural rows and columns: dependencies, a mesh, who talks to whom"""
    nodes, links, layout, size = {}, [], "spring", (5.0, 3.0)
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "node":
            nodes[rest[0]] = dict(label=caps(rest[1]) if len(rest) > 1 else caps(rest[0]),
                                  shape=next((o for o in rest[2:] if o in ("box", "round", "dash", "drum")), "round"))
        elif kind == "link":
            for k in rest[:2]:
                nodes.setdefault(k, dict(label=caps(k), shape="round"))
            label = next((o for o in rest[2:] if o not in ("dash", "arrow")), "")
            links.append((rest[0], rest[1], caps(label), "dash" in rest[2:], "arrow" in rest[2:]))
        elif kind == "layout":
            layout = rest[0]
        elif kind == "size":
            size = (float(rest[0]), float(rest[1]))
    ids = list(nodes)
    n = len(ids)
    if not n:
        raise SystemExit("handbook: network has no nodes")
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    pos = np.c_[np.cos(ang), np.sin(ang)]
    if layout == "spring" and n > 2:                  # Fruchterman-Reingold from the circle, deterministic
        idx = {k: i for i, k in enumerate(ids)}
        k_ = 1.6 / np.sqrt(n)
        temp = 0.2
        for _ in range(300):
            d = pos[:, None, :] - pos[None, :, :]
            dist = np.linalg.norm(d, axis=2) + 1e-9
            disp = (d / dist[..., None] * (k_ ** 2 / dist)[..., None]).sum(axis=1)
            for a, b, *_ in links:
                i, j = idx[a], idx[b]
                delta = pos[i] - pos[j]
                f = np.linalg.norm(delta) ** 2 / k_
                step = delta / (np.linalg.norm(delta) + 1e-9) * f
                disp[i] -= step; disp[j] += step
            length = np.linalg.norm(disp, axis=1)[:, None] + 1e-9
            pos += disp / length * np.minimum(length, temp)
            temp *= 0.985
    pos -= pos.min(axis=0)
    pos /= np.where(pos.max(axis=0) > 0, pos.max(axis=0), 1)
    W, H = size
    xy = {k: (0.6 + pos[i, 0] * (W - 1.2), 0.3 + pos[i, 1] * (H - 0.6)) for i, k in enumerate(ids)}
    bw, bh = 0.85, 0.3
    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=size)
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
        ax.set_xlim(0, W); ax.set_ylim(0, H)
        patches = {}
        for k, nd in nodes.items():
            x, y = xy[k]
            rad = 0.14 if nd["shape"] == "round" else 0.0
            patches[k] = ax.add_patch(FancyBboxPatch((x - bw / 2, y - bh / 2), bw, bh, fc="white", ec=INK, lw=0.8,
                                                     boxstyle=f"round,pad=0,rounding_size={rad}", zorder=2,
                                                     ls=(0, (4, 2)) if nd["shape"] == "dash" else "-"))
            ax.text(x, y, nd["label"], fontsize=5.6, ha="center", va="center", zorder=3, linespacing=1.05)
        for a, b, label, dash, arrow in links:
            ax.add_patch(FancyArrowPatch(xy[a], xy[b], patchA=patches[a], patchB=patches[b],
                                         arrowstyle="-|>" if arrow else "-", mutation_scale=7, color=INK, lw=0.7,
                                         ls=(0, (4, 2.5)) if dash else "-", zorder=1))
            if label:
                ax.text((xy[a][0] + xy[b][0]) / 2, (xy[a][1] + xy[b][1]) / 2, label, fontsize=5, ha="center",
                        va="center", bbox=dict(fc="white", ec="none", pad=0.4), zorder=1.5)
        return svg(fig)


# -- contour ---------------------------------------------------------------------------------------------------------

def contour(spec):
    """fn "EXPR"                     (a field f(x, y) in the fn terms of :::plot, with y as well as x)
       range X0 X1 Y0 Y1 [N]         (the window; N points a side, default 200)
       levels V V V ... | levels N   (the contour values, or how many)
       xlabel "LABEL" / ylabel "LABEL"
       point X Y "LABEL"             (a marked spot: a source, a station, a design point)
       arrows N                      (the field, minus the gradient of f, as N by N arrows of length by strength:
                                      flow down a potential, wind round a low; arrows 0 for none)
       size W H                      (inches; default 3.4 by 2.8)"""
    src, rng, levels, xlabel, ylabel, pts, size = None, (-1, 1, -1, 1, 200), 8, "", "", [], (3.4, 2.8)
    arrows = 0
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "fn":
            src = rest[0]
        elif kind == "range":
            rng = tuple(float(v) for v in rest[:4]) + ((int(rest[4]),) if len(rest) > 4 else (200,))
        elif kind == "levels":
            levels = int(rest[0]) if len(rest) == 1 and rest[0].isdigit() else [float(v) for v in rest]
        elif kind == "xlabel":
            xlabel = caps(rest[0])
        elif kind == "ylabel":
            ylabel = caps(rest[0])
        elif kind == "point":
            pts.append((float(rest[0]), float(rest[1]), caps(rest[2]) if len(rest) > 2 else ""))
        elif kind == "arrows":
            arrows = int(rest[0])
        elif kind == "size":
            size = (float(rest[0]), float(rest[1]))
    if not src:
        raise SystemExit("handbook: contour needs a fn line")
    x0, x1, y0, y1, n = rng
    X, Y = np.meshgrid(np.linspace(x0, x1, int(n)), np.linspace(y0, y1, int(n)))
    Z = _fn(src, X, y=Y)
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=size)
        cs = ax.contour(X, Y, Z, levels=levels, colors=INK, linewidths=0.6)
        ax.clabel(cs, fontsize=5, fmt="%g", inline_spacing=2)
        if arrows:
            ax_, ay_ = np.meshgrid(np.linspace(x0, x1, arrows + 2)[1:-1], np.linspace(y0, y1, arrows + 2)[1:-1])
            h = 1e-4 * max(x1 - x0, y1 - y0)
            u = -(_fn(src, ax_ + h, y=ay_) - _fn(src, ax_ - h, y=ay_)) / (2 * h)
            v = -(_fn(src, ax_, y=ay_ + h) - _fn(src, ax_, y=ay_ - h)) / (2 * h)
            mag = np.hypot(u, v)
            cap = np.nanpercentile(mag, 90) or 1                # the strongest tenth drawn at full length
            k = np.minimum(mag, cap) / np.where(mag > 0, mag, 1)
            ax.quiver(ax_, ay_, u * k, v * k, color=INK, width=0.004, headwidth=3.5, headlength=4, pivot="mid",
                      scale=cap * arrows * 1.3, scale_units="width")
        for x, y, label in pts:
            ax.plot([x], [y], marker="+", ms=6, mec=INK, mew=0.9)
            if label:
                ax.annotate(label, xy=(x, y), xytext=(4, 3), textcoords="offset points", fontsize=5.4,
                            bbox=dict(fc="white", ec="none", pad=0.3))
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel(xlabel, fontsize=6); ax.set_ylabel(ylabel, fontsize=6)
        return svg(fig)


# -- polar -----------------------------------------------------------------------------------------------------------

def polar(spec):
    """fn "EXPR" ["LABEL"]           (r as a function of t, the angle in radians: an antenna pattern, a cardioid)
       rose DIRECTION VALUE          (a wedge on a compass rose: DIRECTION in degrees from north, clockwise, or N NE E ...)
       width DEGREES                 (each rose wedge's width; default 22.5, the 16 points of the compass)
       compass                       (north up and clockwise, as for a wind rose; implied by rose)
       db                            (r is in dB, the outer ring 0)
       size W                        (inches; default 2.8)"""
    fns, rose, width, compass, db, size = [], [], None, False, False, 2.8
    names = {"N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5, "E": 90, "ESE": 112.5, "SE": 135, "SSE": 157.5, "S": 180,
             "SSW": 202.5, "SW": 225, "WSW": 247.5, "W": 270, "WNW": 292.5, "NW": 315, "NNW": 337.5}
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "fn":
            fns.append((rest[0], caps(rest[1]) if len(rest) > 1 else ""))
        elif kind == "rose":
            d = names.get(rest[0].upper())
            rose.append((float(rest[0]) if d is None else d, float(rest[1])))
            compass = True
        elif kind == "width":
            width = float(rest[0])
        elif kind == "compass":
            compass = True
        elif kind == "db":
            db = True
        elif kind == "size":
            size = float(rest[0])
    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=(size, size))
        ax = fig.add_subplot(projection="polar")
        if compass:
            ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)
        t = np.linspace(0, 2 * np.pi, 721)
        for i, (src, label) in enumerate(fns):
            r = _fn(src, t, t=t)
            ax.plot(t, r, color=INK, lw=0.9, ls=DASHES[i % len(DASHES)])
            if label:
                k = int(np.argmax(r))
                ax.annotate(label, xy=(t[k], r[k]), xytext=(4, 4), textcoords="offset points", fontsize=5.4)
        if rose:
            w = np.radians(width or 22.5) * 0.85
            ax.bar([np.radians(d) for d, _ in rose], [v for _, v in rose], width=w, color="white", edgecolor=INK,
                   linewidth=0.7, hatch="//////")
        if db:
            ax.set_rlabel_position(100)
        ax.grid(True, color=INK, lw=0.3, alpha=0.5)
        ax.tick_params(labelsize=5.4)
        if compass:
            ax.set_xticks(np.radians([0, 90, 180, 270]), ["N", "E", "S", "W"])
        return svg(fig)


# -- raster ----------------------------------------------------------------------------------------------------------

def raster(spec, base=Path(".")):
    """csv PATH                      (a grid of numbers, a row a line, no header: a spectrogram, a waterfall, an image)
       fn "EXPR"                     (or a field f(x, y), as for :::contour)
       extent X0 X1 Y0 Y1            (what the grid spans; the first csv row is the top)
       range LO HI                   (the values set white and black; default the data's own)
       xlabel "LABEL" / ylabel "LABEL" / unit "LABEL"   (unit labels the scale bar)
       log                           (shade by the log of the value)
       size W H                      (inches; default 4.4 by 2.4)
     ink only: low values light, high values dark, with a scale at the right"""
    grid, src, ext, lim, xlabel, ylabel, unit, log, size = None, None, None, None, "", "", "", False, (4.4, 2.4)
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "csv":
            with open(base / rest[0], newline="") as fh:
                grid = np.array([[float(v) for v in row] for row in csv.reader(fh) if row])
        elif kind == "fn":
            src = rest[0]
        elif kind == "extent":
            ext = tuple(float(v) for v in rest[:4])
        elif kind == "range":
            lim = (float(rest[0]), float(rest[1]))
        elif kind == "xlabel":
            xlabel = caps(rest[0])
        elif kind == "ylabel":
            ylabel = caps(rest[0])
        elif kind == "unit":
            unit = caps(rest[0])
        elif kind == "log":
            log = True
        elif kind == "size":
            size = (float(rest[0]), float(rest[1]))
    ext = ext or (0, 1, 0, 1)
    if grid is None and src:
        X, Y = np.meshgrid(np.linspace(ext[0], ext[1], 300), np.linspace(ext[3], ext[2], 200))
        grid = _fn(src, X, y=Y)
    if grid is None:
        raise SystemExit("handbook: raster needs a csv or a fn line")
    data = np.log10(np.clip(grid, 1e-12, None)) if log else grid
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=size)
        im = ax.imshow(data, cmap="Greys", extent=ext, aspect="auto", interpolation="nearest",
                       vmin=lim[0] if lim else None, vmax=lim[1] if lim else None)
        bar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
        bar.outline.set_linewidth(0.6); bar.ax.tick_params(labelsize=5.4, width=0.5)
        bar.set_label(("LOG10 " if log else "") + unit, fontsize=5.6)
        ax.set_xlabel(xlabel, fontsize=6); ax.set_ylabel(ylabel, fontsize=6)
        return svg(fig)


# -- map -------------------------------------------------------------------------------------------------------------

def _read_shapes(path):
    """[(properties, kind, [ring or line of (lon, lat)])] from GeoJSON, or from a shapefile with its .dbf"""
    import json
    import struct
    path = Path(path)
    out = []
    if path.suffix == ".shp":
        data = path.read_bytes()
        props = _dbf(path.with_suffix(".dbf")) if path.with_suffix(".dbf").exists() else []
        pos, i = 100, 0
        while pos < len(data):
            length = struct.unpack(">i", data[pos + 4:pos + 8])[0]
            rec = data[pos + 8: pos + 8 + 2 * length]
            pos += 8 + 2 * length
            kind = struct.unpack("<i", rec[:4])[0]
            p = props[i] if i < len(props) else {}
            i += 1
            if kind == 1:
                out.append((p, "point", [[struct.unpack("<dd", rec[4:20])]]))
            elif kind in (3, 5):
                nparts, npts = struct.unpack("<ii", rec[36:44])
                parts = list(struct.unpack(f"<{nparts}i", rec[44:44 + 4 * nparts])) + [npts]
                b = 44 + 4 * nparts
                pts = [struct.unpack("<dd", rec[b + 16 * k: b + 16 * k + 16]) for k in range(npts)]
                out.append((p, "line" if kind == 3 else "polygon", [pts[a:z] for a, z in zip(parts, parts[1:])]))
        return out
    gj = json.loads(path.read_text())
    feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
    for f in feats:
        g, p = f.get("geometry") or {}, f.get("properties") or {}
        t, c = g.get("type"), g.get("coordinates")
        if t == "Point":
            out.append((p, "point", [[c]]))
        elif t == "MultiPoint":
            out.append((p, "point", [c]))
        elif t == "LineString":
            out.append((p, "line", [c]))
        elif t == "MultiLineString":
            out.append((p, "line", c))
        elif t == "Polygon":
            out.append((p, "polygon", c))
        elif t == "MultiPolygon":
            out.append((p, "polygon", [ring for poly in c for ring in poly]))
    return out


def _dbf(path):
    import struct
    data = Path(path).read_bytes()
    nrec, hlen, rlen = struct.unpack("<IHH", data[4:12])
    fields, pos = [], 32
    while data[pos] != 0x0D:
        fields.append((data[pos:pos + 11].split(b"\0")[0].decode(), data[pos + 16]))
        pos += 32
    rows = []
    for i in range(nrec):
        rec, row, p = data[hlen + i * rlen + 1: hlen + (i + 1) * rlen], {}, 0
        for name, size in fields:
            row[name] = rec[p:p + size].decode("latin-1").replace("\0", "").strip()
            p += size
        rows.append(row)
    return rows


def map(spec, base=Path(".")):
    """layer PATH [line|fill|hatch|heavy|dash] [key=PROPERTY]
                                     (GeoJSON or a shapefile, drawn in order: line for outlines, fill for a light tint,
                                      hatch for an area such as a forecast cone, heavy and dash for weight)
       value "NAME" V                (shade the feature whose key property is NAME by V: a choropleth, keyed below)
       extent LON0 LON1 LAT0 LAT1    (the window, in degrees; default all the layers)
       point LON LAT ["LABEL"] [dot|ring|cross|star]
       route LON LAT LON LAT ... ["LABEL"] [dash]     (a track or a path, joined in order)
       graticule STEP                (a lat-lon grid every STEP degrees, lettered at the edges)
       scale KM                      (a scale bar that long)
       size W                        (inches wide; the height follows the extent; default 5)
     projection: equirectangular, squeezed by cos(latitude) at the middle, true enough for a region"""
    layers, values, ext, pts, routes, grat, scale, width = [], {}, None, [], [], None, None, 5.0
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        opts = dict(o.split("=", 1) for o in rest if "=" in o)
        words = [r for r in rest if "=" not in r]
        if kind == "layer":
            layers.append((_read_shapes(base / words[0]), set(words[1:]) or {"line"}, opts.get("key")))
        elif kind == "value":
            values[words[0]] = float(words[1])
        elif kind == "extent":
            ext = tuple(float(v) for v in words[:4])
        elif kind == "point":
            label = next((w for w in words[2:] if w not in ("dot", "ring", "cross", "star")), "")
            style = next((w for w in words[2:] if w in ("dot", "ring", "cross", "star")), "dot")
            pts.append((float(words[0]), float(words[1]), caps(label), style))
        elif kind == "route":
            nums = [w for w in words if _isnum(w)]
            label = next((w for w in words if not _isnum(w) and w != "dash"), "")
            routes.append((list(zip(map_float(nums[0::2]), map_float(nums[1::2]))), caps(label), "dash" in words))
        elif kind == "graticule":
            grat = float(words[0])
        elif kind == "scale":
            scale = float(words[0])
        elif kind == "size":
            width = float(words[0])
    if ext is None:
        allp = [q for shapes, _, _ in layers for _, _, parts in shapes for part in parts for q in part]
        allp += [(x, y) for x, y, _, _ in pts] + [q for r, _, _ in routes for q in r]
        if not allp:
            raise SystemExit("handbook: map has nothing to draw")
        xs_, ys_ = [q[0] for q in allp], [q[1] for q in allp]
        ext = (min(xs_), max(xs_), min(ys_), max(ys_))
    lon0, lon1, lat0, lat1 = ext
    k = np.cos(np.radians((lat0 + lat1) / 2))
    proj = lambda lon, lat: ((lon - lon0) * k, lat - lat0)
    w_deg, h_deg = (lon1 - lon0) * k, lat1 - lat0
    height = width * h_deg / w_deg
    vmax = max(values.values(), default=1) or 1
    vmin = min(values.values(), default=0)
    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=(width, height + (0.35 if values else 0)))
        ax = fig.add_axes([0, (0.35 / (height + 0.35)) if values else 0, 1, height / (height + (0.35 if values else 0))])
        ax.set_xlim(0, w_deg); ax.set_ylim(0, h_deg); ax.set_aspect("equal")
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(True); sp.set_linewidth(1.0)
        for shapes, style, key in layers:
            for props, kind, parts in shapes:
                name = str(props.get(key, "")) if key else ""
                v = values.get(name)
                for part in parts:
                    xy = [proj(lon, lat) for lon, lat in part]
                    if kind == "polygon":
                        tint = (str(1 - 0.75 * (v - vmin) / ((vmax - vmin) or 1)) if v is not None else
                                "#ececec" if "fill" in style else "none")
                        ax.add_patch(plt.Polygon(xy, closed=True, fc=tint, ec=INK, hatch="//////" if "hatch" in style else None,
                                                 lw=1.0 if "heavy" in style else 0.45,
                                                 ls=(0, (4, 2)) if "dash" in style else "-"))
                    elif kind == "line":
                        ax.plot(*zip(*xy), color=INK, lw=1.0 if "heavy" in style else 0.5,
                                ls=(0, (4, 2)) if "dash" in style else "-")
                    else:
                        ax.plot(*zip(*xy), ls="none", marker="o", ms=1.6, color=INK)
        if grat:
            for lon in np.arange(np.ceil(lon0 / grat) * grat, lon1 + 1e-9, grat):
                ax.plot([proj(lon, lat0)[0]] * 2, [0, h_deg], color=INK, lw=0.25, ls=(0, (1, 2)))
                ax.text(proj(lon, lat0)[0], -0.05 * h_deg / 3, f"{abs(lon):g}°{'W' if lon < 0 else 'E'}",
                        fontsize=5, ha="center", va="top")
            for lat in np.arange(np.ceil(lat0 / grat) * grat, lat1 + 1e-9, grat):
                ax.plot([0, w_deg], [lat - lat0] * 2, color=INK, lw=0.25, ls=(0, (1, 2)))
                ax.text(-0.02 * w_deg / 3, lat - lat0, f"{abs(lat):g}°{'S' if lat < 0 else 'N'}", fontsize=5,
                        ha="right", va="center")
        for r, label, dash in routes:
            xy = [proj(*q) for q in r]
            ax.plot(*zip(*xy), color=INK, lw=1.1, ls=(0, (4, 2)) if dash else "-", zorder=4)
            if label:
                ax.annotate(label, xy=xy[-1], xytext=(4, 3), textcoords="offset points", fontsize=5.6,
                            bbox=dict(fc="white", ec="none", pad=0.4), zorder=5)
        for lon, lat, label, style in pts:
            x, y = proj(lon, lat)
            m = {"dot": ("o", INK), "ring": ("o", "white"), "cross": ("+", INK), "star": ("*", INK)}[style]
            ax.plot([x], [y], marker=m[0], ms=4 if style != "star" else 6, mfc=m[1], mec=INK, mew=0.8, zorder=6)
            if label:
                ax.annotate(label, xy=(x, y), xytext=(4, 3), textcoords="offset points", fontsize=5.6, zorder=6,
                            bbox=dict(fc="white", ec="none", pad=0.4))
        if scale:
            deg = scale / (111.32 * k) * k              # km to projected units along the parallel
            x0_, y0_ = 0.04 * w_deg, 0.05 * h_deg
            ax.add_patch(Rectangle((x0_, y0_), deg, 0.012 * h_deg + 0.02, fc=INK, ec=INK, zorder=7))
            ax.text(x0_ + deg / 2, y0_ + 0.03 * h_deg, f"{scale:g} KM", fontsize=5.4, ha="center", va="bottom",
                    zorder=7, bbox=dict(fc="white", ec="none", pad=0.3))
        if values:                                   # the key for a choropleth: light to dark
            kx = fig.add_axes([0.3, 0.02, 0.4, 0.25 / (height + 0.35)])
            kx.imshow(np.linspace(0, 1, 100)[None, :], cmap="Greys", vmin=0, vmax=1 / 0.75, aspect="auto",
                      extent=(vmin, vmax, 0, 1))
            kx.set_yticks([]); kx.tick_params(labelsize=5.2, length=2)
            for sp in kx.spines.values():
                sp.set_linewidth(0.5)
        return svg(fig)


def map_float(seq):
    return [float(v) for v in seq]
