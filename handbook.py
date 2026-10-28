"""Line-art figures for APOLLO style review sheets, after the Apollo Operations Handbook: black ink, no colour, narrow capitals,
dashed fences round subsystems, drums for storage, filled arrowheads. Everything returns SVG text with live fonts
(svg.fonttype none), so the browser sets the lettering in the same faces as the sheet.

  diagram(spec)    functional block diagram from text lines (see sheet.py's docstring for the syntax)
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
  svg(fig)         any matplotlib figure, styled with STYLE, as SVG text
"""
import csv
import io
import shlex
from pathlib import Path

import matplotlib

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
            yield shlex.split(raw)


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
       fence "LABEL" ID ID ...
       note COL ROW "TEXT"                      (small free lettering)
       grid DX DY                               (inches between columns and rows; default 1.55 0.78)"""
    global DX, DY
    nodes, edges, fences, notes, loops = {}, [], [], [], []
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
            label = next((o for o in rest[2:] if o not in ("dash", "both") and not o.startswith("bend=")), "")
            bend = next((float(o[5:]) for o in rest[2:] if o.startswith("bend=")), None)
            edges.append(dict(a=rest[0], b=rest[1], label=caps(label), dash="dash" in rest[2:], both="both" in rest[2:],
                              bend=bend))
        elif kind == "loop":
            loops.append((rest[0], caps(next((o for o in rest[1:] if o not in ("top", "bottom")), "")),
                          "bottom" in rest[1:]))
        elif kind == "fence":
            fences.append(dict(label=caps(rest[0]), ids=rest[1:]))
        elif kind == "note":
            notes.append((float(rest[0]) * DX, -float(rest[1]) * DY, caps(rest[2])))
    xs = [n["x"] + s * n["w"] / 2 for n in nodes.values() for s in (-1, 1)] + [x for x, _, _ in notes]
    ys = [n["y"] + s * n["h"] / 2 for n in nodes.values() for s in (-1, 1)] + [y for _, y, _ in notes]
    for e in edges:                                # a curve's crown can stand outside the boxes
        if e["bend"] is not None:
            cx, cy = _crown(nodes[e["a"]], nodes[e["b"]], e["bend"])
            xs.append(cx); ys.append(cy)
    for k, _, under in loops:
        ys.append(nodes[k]["y"] + (-1 if under else 1) * (nodes[k]["h"] / 2 + 0.42))
    pad = 0.35
    x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=(x1 - x0, y1 - y0))
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_axis_off()
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
            if e["label"]:
                seg = max(zip(pts[:-1], pts[1:]), key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
                mx, my = (seg[0][0] + seg[1][0]) / 2, (seg[0][1] + seg[1][1]) / 2
                flat = abs(seg[1][1] - seg[0][1]) < 1e-6
                ax.text(mx, my + (0.05 if flat else 0), e["label"], fontsize=5.2, ha="center" if flat else "left",
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
                                         connectionstyle=f"arc3,rad={e['bend']}", ls=(0, (4, 2.5)) if e["dash"] else "-",
                                         arrowstyle="<|-|>" if e["both"] else "-|>", shrinkA=2, shrinkB=1, **arrow))
            if e["label"]:
                ax.text(*_crown(a, b, e["bend"]), e["label"], fontsize=5.2, ha="center", va="center", linespacing=1.05,
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
       call ROW AT "TEXT"                       (a leader from the bar row to lettering below the axis)"""
    rows, bars, marks, calls = [], [], [], []
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


def plot(spec, base=Path(".")):
    """csv PATH                         (relative to the sheet)
       x COLUMN ["LABEL"]
       y COLUMN ["LABEL"] [dots|step] [every=N]   (a series; dots for measured points, step for a staircase;
                                        every=N keeps every Nth row, so dense dots stay dots)
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
    panels = [dict(series=[], hlines=[], ylabel="", ylim=None, logy=False)]
    xcol, xlabel, logx, rng, xlim, size = None, "", False, None, None, (3.4, 2.2)
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        cur = panels[-1]
        flags = [o for o in rest[1:] if o in ("dots", "step") or o.startswith("every=")]
        words = [o for o in rest[1:] if o not in flags]
        if kind == "csv":
            with open(base / rest[0], newline="") as fh:
                for row in csv.DictReader(fh):
                    for k, v in row.items():
                        cols.setdefault(k, []).append(float(v))
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
            panels.append(dict(series=[], hlines=[], ylabel="", ylim=None, logy=False))
        elif kind == "size":
            size = (6.4, 2.4) if rest[0] == "wide" else (float(rest[0]), float(rest[1]))
    if rng:
        lo, hi, n = rng
        xs = np.geomspace(lo, hi, n) if logx else np.linspace(lo, hi, n)
    else:
        xs = np.asarray(cols[xcol]) if xcol else np.linspace(0, 1, 400)
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(len(panels), 1, sharex=True, squeeze=False,
                                 figsize=(size[0], size[1] * (1 + 0.6 * (len(panels) - 1))))
        for pi_, (ax, pnl) in enumerate(zip(axes[:, 0], panels)):
            for i, (kind, src, label, flags) in enumerate(pnl["series"]):
                if kind == "y":
                    k = next((int(f[6:]) for f in flags if f.startswith("every=")), 1)
                    x, y = np.asarray(cols[xcol])[::k], np.asarray(cols[src])[::k]
                else:
                    x = xs
                    y = np.broadcast_to(eval(src, {"__builtins__": {}}, {**FN, "x": xs}), xs.shape)
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
                        transform=ax.get_yaxis_transform())
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


def budget(spec):
    """bar "LABEL" USED CAPACITY ["UNIT"]  (one gauge a line: the used part hatched, headroom open, figures at the end;
                                          numbers may be hex, 0x8DFBC)
       mark PERCENT "LABEL"               (a dashed limit across every gauge, e.g. 90 "RED AT 90 %")"""
    bars, marks = [], []
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "bar":
            bars.append((caps(rest[0]), float(int(rest[1], 0)) if rest[1].startswith("0x") else float(rest[1]),
                         float(int(rest[2], 0)) if rest[2].startswith("0x") else float(rest[2]),
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
        ax.set_xlim(-0.8, (len(actors) - 1) * dx + 0.8); ax.set_ylim(-(n + 0.8) * dy, 0.8 * dy)
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
                ax.text((X[a] + X[b]) / 2, y - 0.03, label, ha="center", va="bottom", fontsize=5.2)
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
            for k, ch in enumerate("".join(half[c] for c in wave)):
                t = k / 2
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
                ax.text(-0.12, y1, l["at"].upper(), fontsize=5.4, ha="right", va="center")
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
       horizontal                    (categories down the left, values across: for long names)
       log                           (a log value axis)
       size W H                      (inches; default 3.4 by 2.2)"""
    series, cats, unit, stacked, horiz, log, size = [], [], "", False, False, False, (3.4, 2.2)
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
        elif kind == "horizontal":
            horiz = True
        elif kind == "log":
            log = True
        elif kind == "size":
            size = (float(rest[0]), float(rest[1]))
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
                if horiz:
                    ax.barh(-pos, v, width, left=base, **kw)
                else:
                    ax.bar(pos, v, width, bottom=base, **kw)
                if not stacked:
                    _endlabel(ax, f"{v:g}", v, -pos if horiz else pos, horiz)
                base += v if stacked else 0
            if stacked:
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
     yes, part and no print as a full, half and open dot, the handbook's way of comparing at a glance"""
    cols, rows, scale = [], [], None
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "cols":
            cols = [caps(c) for c in rest]
        elif kind == "row":
            rows.append((caps(rest[0]), rest[1:]))
        elif kind == "scale":
            scale = float(rest[0])
    nums = [float(v) for _, vs in rows for v in vs if _isnum(v)]
    scale = scale or (max(nums) if nums else 1)
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
