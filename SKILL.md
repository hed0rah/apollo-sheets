---
name: apollo-sheets
description: Render a Markdown report as a print-ready PDF review sheet in the style of the Apollo Operations Handbook (numbered paragraphs, ruled tables, cautions, checklists, change bars, line-art block diagrams, timelines and plots). Use when the user asks for an Apollo sheet, a handbook-style or NASA-style report, or a printable review sheet of a report, design or procedure.
---

# apollo-sheets

`sheet.py` turns Markdown into a PDF through headless Chrome. Start from `template.md`. The reference sheet
`examples/apollo/apollo.md` shows every block beside its source; `README.md` summarizes the syntax.

## Workflow

1. Write or take the report as Markdown. Add front matter (title, section, tab, system, doc, mission, date).
   Quote any value that contains a colon.
2. Use the blocks where they carry information: `:::diagram` for a signal or data path, `:::timeline` for a
   sequence, `:::plot` for CSV data, `:::table` for anything tabular, `:::checklist` for a procedure,
   `:::caution` / `:::warning` for hazards, `:::sequence` for hand-offs or protocols, `:::signals` for timing,
   `:::budget` for used-against-capacity, `:::equations` and `:::symbols` for derivations. A block that holds
   blocks takes four colons (`::::changed` around `:::equations`).
3. Render with page PNGs and look at every page:

       python <skill dir>/sheet.py report.md --png

4. Fix what overlaps. Diagram edges route with one elbow, so move nodes rather than accept an edge through a
   box; keep timeline `call` lettering clear of the tick labels.

To ingest someone else's report without editing it, set front matter from the command line:
`-s section=3 -s tab=PHY`.

Requirements: python3 with matplotlib and pyyaml, Chrome or Chromium, the URW base35 fonts. `SHEET_FONTS` and
`SHEET_CHROME` override the font directory and browser.
