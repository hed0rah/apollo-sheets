"""Line-art figures for APOLLO style review sheets, after the Apollo Operations Handbook: black ink, no colour, narrow capitals,
dashed fences round subsystems, drums for storage, filled arrowheads. Everything returns SVG text with live fonts
(svg.fonttype none), so the browser sets the lettering in the same faces as the sheet.

  diagram(spec)    functional block diagram from text lines (see sheet.py's docstring for the syntax)
  timeline(spec)   rows of bars on one time axis, with vertical markers
  plot(spec, base) lines from a CSV, labelled at their ends instead of a legend
  svg(fig)         any matplotlib figure, styled with STYLE, as SVG text
"""
import csv
import io
import shlex
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
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


# -- plot from a CSV -------------------------------------------------------------------------------------------------

def plot(spec, base=Path(".")):
    """csv PATH                 (relative to the sheet)
       x COLUMN ["LABEL"]
       y COLUMN ["LABEL"]       (one per line; each line labelled at its right end)
       ylabel "LABEL"
       log x|y|xy
       mark AT "LABEL"          (a vertical line at x = AT)"""
    cols, ys, marks = {}, [], []
    xcol, xlabel, ylabel, log = None, "", "", ""
    for t in _lines(spec):
        kind, rest = t[0], t[1:]
        if kind == "csv":
            with open(base / rest[0], newline="") as fh:
                for row in csv.DictReader(fh):
                    for k, v in row.items():
                        cols.setdefault(k, []).append(float(v))
        elif kind == "x":
            xcol, xlabel = rest[0], caps(rest[1] if len(rest) > 1 else rest[0])
        elif kind == "y":
            ys.append((rest[0], caps(rest[1] if len(rest) > 1 else rest[0])))
        elif kind == "ylabel":
            ylabel = caps(rest[0])
        elif kind == "log":
            log = rest[0]
        elif kind == "mark":
            marks.append((float(rest[0]), caps(rest[1])))
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(3.4, 2.2))
        for i, (col, label) in enumerate(ys):
            ax.plot(cols[xcol], cols[col], color=INK, ls=DASHES[i % len(DASHES)])
            ax.annotate(label, xy=(cols[xcol][-1], cols[col][-1]), xytext=(4, 0), textcoords="offset points",
                        fontsize=5.6, va="center")
        for at, label in marks:
            ax.axvline(at, color=INK, lw=0.6, ls=(0, (3, 2)))
            ax.text(at, 1.0, label, fontsize=5.4, ha="center", va="bottom", transform=ax.get_xaxis_transform())
        if "x" in log:
            ax.set_xscale("log")
        if "y" in log:
            ax.set_yscale("log")
        ax.grid(True, color=INK, lw=0.25, alpha=0.35)
        ax.set_xlabel(xlabel, fontsize=6); ax.set_ylabel(ylabel, fontsize=6)
        return svg(fig)
