"""Line-art figures for APOLLO style review sheets, after the Apollo Operations Handbook: black ink, no colour, narrow capitals,
dashed fences round subsystems, drums for storage, filled arrowheads. Everything returns SVG text with live fonts
(svg.fonttype none), so the browser sets the lettering in the same faces as the sheet.

  diagram(spec)    functional block diagram from text lines (see sheet.py's docstring for the syntax)
  timeline(spec)   rows of bars on one time axis, with vertical markers
  plot(spec, base) CSV series and exact functions, labelled at their ends instead of a legend
  budget(spec)     used-of-capacity gauges (memory, power, link budgets)
  sequence(spec)   messages between actors, top to bottom (protocols, install flows)
  signals(spec)    a timing diagram: clocks, lines and buses on one step axis
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
from matplotlib.patches import Ellipse, FancyBboxPatch, Rectangle

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


def _route(a, b):
    """an orthogonal path from a to b: straight when they share a row or column, else one elbow"""
    if abs(a["y"] - b["y"]) < 1e-6:
        s, e = ("r", "l") if b["x"] > a["x"] else ("l", "r")
        return [_anchor(a, s), _anchor(b, e)]
    if abs(a["x"] - b["x"]) < 1e-6:
        s, e = ("b", "t") if b["y"] < a["y"] else ("t", "b")
        return [_anchor(a, s), _anchor(b, e)]
    p = _anchor(a, "r" if b["x"] > a["x"] else "l")
    q = _anchor(b, "t" if b["y"] < a["y"] else "b")
    return [p, (q[0], p[1]), q]


def diagram(spec):
    """node ID "LABEL" COL ROW [box|drum|round|dash|text] [w=COLS] [h=ROWS]
       edge FROM TO ["LABEL"] [dash] [both]
       fence "LABEL" ID ID ...
       note COL ROW "TEXT"                      (small free lettering)
       grid DX DY                               (inches between columns and rows; default 1.55 0.78)"""
    global DX, DY
    nodes, edges, fences, notes = {}, [], [], []
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
            label = next((o for o in rest[2:] if o not in ("dash", "both")), "")
            edges.append(dict(a=rest[0], b=rest[1], label=caps(label), dash="dash" in rest[2:], both="both" in rest[2:]))
        elif kind == "fence":
            fences.append(dict(label=caps(rest[0]), ids=rest[1:]))
        elif kind == "note":
            notes.append((float(rest[0]) * DX, -float(rest[1]) * DY, caps(rest[2])))
    xs = [n["x"] + s * n["w"] / 2 for n in nodes.values() for s in (-1, 1)] + [x for x, _, _ in notes]
    ys = [n["y"] + s * n["h"] / 2 for n in nodes.values() for s in (-1, 1)] + [y for _, y, _ in notes]
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
        for e in edges:
            pts = _route(nodes[e["a"]], nodes[e["b"]])
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
            elif n["shape"] != "text":
                rad = 0.08 if n["shape"] == "round" else 0.0
                ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle=f"round,pad=0,rounding_size={rad}",
                                            fc="white", ec=INK, lw=0.9,
                                            ls=(0, (4, 2)) if n["shape"] == "dash" else "-"))
            ax.text(x, y - (0.02 if n["shape"] == "drum" else 0), n["label"], ha="center", va="center", fontsize=6,
                    linespacing=1.1)
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
                                  "sign", "pi", "e", "hypot", "arctan2", "sinc")}


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
       mark AT "LABEL"                  (vertical line at x = AT)
       hline AT "LABEL"                 (horizontal line at y = AT: a limit, a threshold)
       size wide | size W H             (inches; default 3.4 x 2.2, wide 6.4 x 2.4)
     every series is labelled at its right end, so there is no legend to look up"""
    cols, series, marks, hlines = {}, [], [], []
    xcol, xlabel, ylabel, log, rng, xlim, ylim, size = None, "", "", "", None, None, None, (3.4, 2.2)
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
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
            series.append((kind, rest[0], caps(words[0]) if words else ("" if kind == "fn" else caps(rest[0])), flags))
        elif kind == "range":
            rng = (float(rest[0]), float(rest[1]), int(rest[2]) if len(rest) > 2 else 400)
        elif kind == "xlabel":
            xlabel = caps(rest[0])
        elif kind == "ylabel":
            ylabel = caps(rest[0])
        elif kind in ("xlim", "ylim"):
            lim = (float(rest[0]), float(rest[1]))
            xlim, ylim = (lim, ylim) if kind == "xlim" else (xlim, lim)
        elif kind == "log":
            log = rest[0]
        elif kind == "mark":
            marks.append((float(rest[0]), caps(rest[1])))
        elif kind == "hline":
            hlines.append((float(rest[0]), caps(rest[1]) if len(rest) > 1 else ""))
        elif kind == "size":
            size = (6.4, 2.4) if rest[0] == "wide" else (float(rest[0]), float(rest[1]))
    if rng:
        lo, hi, n = rng
        xs = np.geomspace(lo, hi, n) if "x" in log else np.linspace(lo, hi, n)
    else:
        xs = np.asarray(cols[xcol]) if xcol else np.linspace(0, 1, 400)
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=size)
        for i, (kind, src, label, flags) in enumerate(series):
            if kind == "y":
                k = next((int(f[6:]) for f in flags if f.startswith("every=")), 1)
                x, y = np.asarray(cols[xcol])[::k], np.asarray(cols[src])[::k]
            else:
                x = xs
                y = np.broadcast_to(eval(src, {"__builtins__": {}}, {**FN, "x": xs}), xs.shape)
            if "dots" in flags:
                ax.plot(x, y, ls="none", marker="o", ms=2.6, mfc="white", mec=INK, mew=0.7)
            else:
                ax.plot(x, y, color=INK, ls=DASHES[i % len(DASHES)], drawstyle="steps-post" if "step" in flags else "default")
            if label:
                ax.annotate(label, xy=(x[-1], y[-1]), xytext=(4, 0), textcoords="offset points", fontsize=5.6,
                            va="center", annotation_clip=False)
        for at, label in marks:
            ax.axvline(at, color=INK, lw=0.6, ls=(0, (3, 2)))
            ax.text(at, 1.0, label, fontsize=5.4, ha="center", va="bottom", transform=ax.get_xaxis_transform())
        for at, label in hlines:
            ax.axhline(at, color=INK, lw=0.6, ls=(0, (3, 2)))
            ax.text(0.99, at, label, fontsize=5.4, ha="right", va="bottom", transform=ax.get_yaxis_transform())
        if "x" in log:
            ax.set_xscale("log")
        if "y" in log:
            ax.set_yscale("log")
        if xlim:
            ax.set_xlim(*xlim)
        if ylim:
            ax.set_ylim(*ylim)
        ax.grid(True, color=INK, lw=0.25, alpha=0.35)
        ax.set_xlabel(xlabel, fontsize=6); ax.set_ylabel(ylabel, fontsize=6)
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
