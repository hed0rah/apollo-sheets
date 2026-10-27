---
title: Custom figures
section: "7"
tab: FIG
handbook: Operations Handbook
system: Drawing your own line art
doc: FIG-7
mission: EXAMPLE-1
date: 10.27.2026
change: 10.27.2026
by: any matplotlib figure, in the handbook's ink and lettering
---

## Method

When the built-in diagram, timeline and plot blocks are not enough, draw the figure in matplotlib inside
`handbook.STYLE`, write it out with `handbook.svg(fig)`, and include the SVG as an image. The lettering stays
live text, so the browser sets it in the same narrow face as the rest of the sheet.

```
with plt.rc_context(handbook.STYLE):
    fig, ax = plt.subplots(figsize=(3.6, 3.2))
    ...                                   # INK and DASHES keep it in the house look
Path("orbit.svg").write_text(handbook.svg(fig))
```

![Hohmann Transfer between Two Circular Orbits](orbit.svg){width=half}

:::note
Run `python orbit.py` to regenerate the SVG; the sheet only reads it.
:::
