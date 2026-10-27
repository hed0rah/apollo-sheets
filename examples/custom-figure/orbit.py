"""a transfer orbit drawn as handbook line art with handbook.svg(); writes orbit.svg beside this file"""
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import handbook  # noqa: E402

r1, r2 = 1.0, 1.52                                  # circular orbits, arbitrary units
a, e = (r1 + r2) / 2, (r2 - r1) / (r2 + r1)
t = np.linspace(0, 2 * np.pi, 400)

with plt.rc_context(handbook.STYLE):
    fig, ax = plt.subplots(figsize=(3.6, 3.2))
    ax.set_aspect("equal"); ax.set_axis_off()
    ax.plot(r1 * np.cos(t), r1 * np.sin(t), color=handbook.INK, lw=0.7)
    ax.plot(r2 * np.cos(t), r2 * np.sin(t), color=handbook.INK, lw=0.7, ls=handbook.DASHES[1])
    nu = np.linspace(0, np.pi, 200)
    r = a * (1 - e * e) / (1 + e * np.cos(nu))
    ax.plot(r * np.cos(nu), r * np.sin(nu), color=handbook.INK, lw=1.4)
    ax.plot(0, 0, marker="o", ms=7, mfc="white", mec=handbook.INK)
    for (x, y), label, off in [((r1, 0), "BURN 1\nDEPARTURE", (0.8, -0.5)), ((-r2, 0), "BURN 2\nARRIVAL", (-0.45, -0.55))]:
        ax.plot(x, y, marker="+", ms=8, mew=1.2, color=handbook.INK)
        ax.annotate(label, xy=(x, y), xytext=(x + off[0], y + off[1]), fontsize=6, ha="center",
                    arrowprops=dict(arrowstyle="-", color=handbook.INK, lw=0.5))
    ax.text(0, 0.18, "PRIMARY", fontsize=6, ha="center")
    lead = dict(arrowstyle="-", color=handbook.INK, lw=0.5)
    nu60 = a * (1 - e * e) / (1 + e * np.cos(np.pi / 3))
    ax.annotate("TRANSFER ELLIPSE", xy=(nu60 * np.cos(np.pi / 3), nu60 * np.sin(np.pi / 3)), xytext=(1.25, 1.55),
                fontsize=5.6, arrowprops=lead)
    ax.annotate("PARKING ORBIT", xy=(0.707, -0.707), xytext=(1.0, -1.7), fontsize=5.6, arrowprops=lead)
    ax.annotate("TARGET ORBIT", xy=(-1.075, -1.075), xytext=(-1.9, -1.6), fontsize=5.6, arrowprops=lead)
(HERE / "orbit.svg").write_text(handbook.svg(fig))
