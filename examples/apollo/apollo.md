---
title: APOLLO style review sheets
section: A
tab: APO
handbook: Operations Handbook
system: APOLLO style, the review sheet format
doc: APOLLO-REF
mission: EXAMPLE-1
date: 10.27.2026
change: 10.27.2026
by: "Reference and specimen sheet. Every block the format has, with its source beside it. Start a new sheet from template.md."
---

## Functional description

A review sheet is a section of a handbook made from one agent's report: numbered paragraphs, figures and tables
with drawing numbers, call-outs, checklists and equations, printed in black on US Letter to be read with a pen.
The report is plain Markdown; `sheet.py` renders it as it is, and the `:::` blocks below add the handbook furniture.
Figures are drawn by `handbook.py` as line art with live lettering, equations by matplotlib's mathtext, and the page
by headless Chrome from HTML and `sheet.css`.

:::diagram Review Sheet Functional Diagram
grid 1.45 0.8
node fm "FRONT MATTER\n-s KEY=VALUE" 1 0 dash
node mt "MATHTEXT\nEQUATIONS" 2 0
node rep "AGENT REPORT\n(MARKDOWN)" 0 1 round
node sheet "SHEET.PY" 1 1
node html "HTML\n+ SHEET.CSS" 2 1
node chrome "HEADLESS\nCHROME" 3 1
node pdf "SHEET PDF\n(US LETTER)" 4 1 round
node hb "HANDBOOK.PY\nFIGURES" 2 2
node fonts "URW BASE35\nFONTS" 3 2 drum
node png "PAGE PNGS\n(--PNG)" 4 2 dash
edge rep sheet
edge fm sheet
edge sheet html
edge mt html "SVG"
edge hb html "SVG"
edge html chrome
edge fonts chrome
edge chrome pdf
edge pdf png "PDFTOPPM"
:::

```
python sheet.py report.md                         writes report.pdf beside it
python sheet.py report.md -o out.pdf --png        and page PNGs, to look without a printer
python sheet.py notes.md -s section=3 -s tab=PHY  someone else's report, without editing it
```

## Page design

:::table Design Rules
| Element | Set in | Rule |
|---|---|---|
| Body | Nimbus Roman 9.6 pt on 1.32 | justified and hyphenated; the first line after a heading indented 0.3 in |
| Lettering on figures | Nimbus Sans Narrow, 5 to 7 pt | capitals only; the same face live in the PDF, never outlines |
| Checklists, code | Nimbus Mono PS 8.3 pt | a checklist is boxed, under a black bar carrying its title and role |
| Page | US Letter | margins 0.95 in top, 0.85 bottom, 0.45 left, 0.3 right; a 0.95 in gutter for numbers |
| Ink | black only | white paper to print; `paper: cream` for a screen copy |
| Headings | `##` capitals, `###` underlined | the paragraph number hangs in the gutter: A.4, A.4.2 |
| Numbers | Figure A-1, Table A-1, (A-1) | figures and tables count through the section; table titles above, captions below |
| Drawing numbers | APO-501A ... | one per figure, bottom right, from the tab |
| Strokes | 0.6 to 0.9 pt | dashed for optional or planned, hatched for used or selected, solid black for on |
| Series | dash pattern, end label | solid, dashed, dotted, dash-dot; labelled at the line's end, never by colour or legend |
| Header, footer | doc, handbook, system; mission, dates, page | dates MM.DD.YYYY; page A-n from the section |
| Changes | bar in the gutter | `:::changed` beside anything altered after the basic date; set `change:` |
:::

The page is quiet on purpose: no colour, no shading but hatch, no rules but the table frames and the `---` line.
Anything that needs colour to be read needs redrawing, not colouring; a colour screen capture prints inverted to
ink with `gray=1`.

## Text and call-outs

### Headings and paragraphs
A `#` heading names the sheet when there is no `title`; a later `#` starts a part on a new page. `##`, `###` and
`####` are numbered from `section`, and any number the report gave its own headings is dropped. Inline marks:
`**bold**`, `*italic*`, `_underline_`, backticks for code, `^sup^`, `~sub~`, `$math$`, and ` -- ` for a dash. Links
keep their words; paper has no links. A line starting `<!--` opens a comment that never prints, up to `-->`.

### Call-outs and checklists

::::row
```
:::caution
Text that, if ignored, costs
time or data.
:::

:::warning
Text that, if ignored, damages
hardware or loses work for good.
:::

:::note
Anything worth a box that is
neither.
:::
```
|||
:::caution
Text that, if ignored, costs time or data.
:::

:::warning
Text that, if ignored, damages hardware or loses work for good.
:::

:::note
Anything worth a box that is neither.
:::
::::

::::row
```
:::checklist Render a Sheet | Any
1  python sheet.py r.md --png
2  read every page PNG
3  fix, render again
:::

:::changed
A paragraph altered after the
basic date.
:::
```
|||
:::checklist Render a Sheet | Any
1  python sheet.py r.md --png
2  read every page PNG
3  fix, render again
:::

:::changed
A paragraph altered after the basic date. The bar is in the gutter, beside the paragraph number.
:::
::::

## Mathematics

### Inline and display
Inline math sits on the baseline of the text: the corner of an RC low-pass is $f_c = 1/(2\pi R C)$, written
`$f_c = 1/(2\pi R C)$`. A display, `$$ ... $$` on its own lines, is centred and numbered from the section:

$$ |H(f)| = \frac{1}{\sqrt{1 + (f/f_c)^{2n}}} $$

:::symbols
f | frequency | Hz
f_c | corner frequency, where the gain is down 3 dB | Hz
n | order of the Butterworth filter |
:::

The `:::symbols` block above is the handbook's "where" list: one `SYMBOL | MEANING | UNIT` a line, the symbol in
TeX without dollars.

### Aligned equations
`:::equations` sets one equation a line, aligned on its first relation (or on `&` where a line has one). A line that
starts with a relation continues the one above and takes no number. Here, the length of an audio block:

::::row
```
:::equations
T_{\mathrm{block}} = N / f_s
= 128 / 44100\ \mathrm{s}
\approx 2.902\ \mathrm{ms}
G_{\mathrm{dB}}(f_c) = {-10} \log_{10} 2
\approx {-3.01}\ \mathrm{dB}
:::
```
|||
:::equations
T_{\mathrm{block}} = N / f_s
= 128 / 44100\ \mathrm{s}
\approx 2.902\ \mathrm{ms}
G_{\mathrm{dB}}(f_c) = {-10} \log_{10} 2
\approx {-3.01}\ \mathrm{dB}
:::
::::

### A result, boxed
`$$\boxed{...}$$` frames the line a reader should carry away:

$$ \boxed{f_c = \frac{1}{2 \pi R C}} $$

:::caution
Equations are set by matplotlib's mathtext, a subset of TeX: fractions, roots, sub- and superscripts, Greek,
`\left( \right)`, accents, `\mathrm`, `\mathbf`, `\mathcal`, sums and integrals. It has no environments
(`\begin{aligned}`, matrices, `cases`): use `:::equations` for alignment, a table for a matrix. `\text{}` is
rewritten to `\mathrm{}` and `\sqrt x` to `\sqrt{x}`. What will not parse prints as its TeX in typewriter, so
nothing is lost: $\begin{pmatrix} a & b \end{pmatrix}$.
:::

## Figures

Every figure is line art with a caption below and a drawing number at its lower right. `:::diagram`,
`:::timeline`, `:::sequence`, `:::signals` and `:::budget` run the width of the column; a `:::plot` is 3.4 by
2.2 in unless it says `size wide` or `size W H`, so two sit side by side in a `::::row`.

### Plots: exact functions and tabulated series
`fn "EXPR"` draws a curve exactly from a numpy expression in `x` (`sin exp sqrt log10 pi where clip` and the
like), over `range LO HI`. `y COLUMN` draws a column of a CSV against `x COLUMN`; `dots` sets it as points, the way
measurements are told from a model. Thresholds are `hline`, events `mark`.

::::row
```
:::plot Butterworth Gain re the Corner
range 0.01 10
fn "-10*log10(1+x**2)" "N = 1"
fn "-10*log10(1+x**4)" "N = 2"
fn "-10*log10(1+x**8)" "N = 4"
log x
xlabel "f / fc"
ylabel "gain, dB"
ylim -85 5
hline -3.01 "-3 DB"
mark 1 "CORNER"
:::
```
|||
:::plot Butterworth Gain re the Corner
range 0.01 10
fn "-10*log10(1+x**2)" "N = 1"
fn "-10*log10(1+x**4)" "N = 2"
fn "-10*log10(1+x**8)" "N = 4"
log x
xlabel "f / fc"
ylabel "gain, dB"
ylim -85 5
hline -3.01 "-3 DB"
mark 1 "CORNER"
:::
::::

::::row
```
:::plot Echo Density, 4 m Cube
csv density.csv
x ms "ms after the click"
y d3 "" dots every=6
fn "4*pi*343**3*(x/1000)**2/4**3" "3D"
log xy
ylabel "echoes per second"
hline 48000 "ONE PER SAMPLE"
:::
```
The dots are a CSV of counts; the line is
$4\pi c^3 t^2 / V$ for $c$ = 343 m/s and
$V$ = 64 m^3^, drawn over the CSV's own x.
|||
:::plot Echo Density, 4 m Cube: CSV (Dots) and Formula (Line)
csv density.csv
x ms "ms after the click"
y d3 "" dots every=6
fn "4*pi*343**3*(x/1000)**2/4**3" "3D"
log xy
ylabel "echoes per second"
hline 48000 "ONE PER SAMPLE"
:::
::::

### Block diagrams
Figure A-1 is a `:::diagram`. Nodes sit on a grid of columns and rows (`grid DX DY` in inches, if the default
1.55 by 0.78 crowds the lettering); edges route themselves straight or with one elbow and are labelled on their
longest run. Shapes: `box`, `round` for ends, `dash` for the optional, `drum` for storage, `text` for bare lettering;
`fence "LABEL" ids...` draws a dashed subsystem boundary.

```
:::diagram Review Sheet Functional Diagram
grid 1.45 0.8
node fm "FRONT MATTER\n-s KEY=VALUE" 1 0 dash
node rep "AGENT REPORT\n(MARKDOWN)" 0 1 round
node sheet "SHEET.PY" 1 1
node fonts "URW BASE35\nFONTS" 3 2 drum
edge rep sheet
edge mt html "SVG"
edge pdf png "PDFTOPPM"
...
:::
```

### Timelines
Rows of bars on one axis, `hatch`, `open` or `solid`; `mark` for a moment across every row, `call` for a leader
to lettering below the axis. Apollo 11, from launch:

```
:::timeline Apollo 11, Ground Elapsed Time
axis "ground elapsed time, hours" 0 200 ticks=25
bar "Earth orbit" 0 2.74 solid
bar "Translunar coast" 2.74 75.83 open
bar "Lunar orbit (CSM)" 75.83 135.40 hatch
bar "LM on the surface" 102.76 124.37 hatch
bar "EVA" 109.13 111.65 solid
bar "Transearth coast" 135.40 195.31 open
mark 102.76 "LANDING" dash
mark 195.31 "SPLASHDOWN" dash
:::
```

:::timeline Apollo 11, Ground Elapsed Time (Launch 07.16.1969, 13:32 UTC)
axis "ground elapsed time, hours" 0 200 ticks=25
bar "Earth orbit" 0 2.74 solid
bar "Translunar coast" 2.74 75.83 open
bar "Lunar orbit (CSM)" 75.83 135.40 hatch
bar "LM on the surface" 102.76 124.37 hatch
bar "EVA" 109.13 111.65 solid
bar "Transearth coast" 135.40 195.31 open
mark 102.76 "LANDING" dash
mark 195.31 "SPLASHDOWN" dash
:::

### Sequence charts
Messages between actors, one step a line, top to bottom: protocols, install flows, a review's hand-offs. `dash`
for a reply, the same actor twice for its own work, `gap` where time passes. A review's hand-offs:

```
:::sequence A Review's Hand-offs
actor agent "REPORTING\nAGENT"
actor writer "SHEET\nWRITER"
actor check "FACT\nCHECKER"
actor owner "OWNER"
msg agent writer "REPORT, SOURCES"
msg writer writer "RENDER, DRAW"
msg writer check "DRAFT PDF"
msg check writer "CORRECTIONS" dash
msg writer owner "FINAL PDF"
gap "LATER"
msg owner writer "A CHANGE" dash
note writer "CHANGE BAR\nCHANGE DATE"
msg writer owner "CHANGED PDF"
:::
```

:::sequence A Review's Hand-offs
actor agent "REPORTING\nAGENT"
actor writer "SHEET\nWRITER"
actor check "FACT\nCHECKER"
actor owner "OWNER"
msg agent writer "REPORT, SOURCES"
msg writer writer "RENDER, DRAW"
msg writer check "DRAFT PDF"
msg check writer "CORRECTIONS" dash
msg writer owner "FINAL PDF"
gap "LATER"
msg owner writer "A CHANGE" dash
note writer "CHANGE BAR\nCHANGE DATE"
msg writer owner "CHANGED PDF"
:::

### Timing diagrams
`:::signals` draws lines and buses on one step axis, a character a step: `0 1` levels, `p n` a clock period
starting high or low, `.` hold, `z` released, `x` unknown, `=` a bus value lettered from a list. An SPI flash
taking the JEDEC read-ID command 0x9F in mode 0, shifted on the falling edge and sampled on the rising:

```
:::signals SPI Mode 0, Command 0x9F (Read JEDEC ID)
signal "CS#" 1000000001
signal "SCLK" 0nnnnnnnn0
signal "MOSI" x========x "1,0,0,1,1,1,1,1"
signal "MISO" zzzzzzzzzz
mark 1 "CS# LOW, BIT 7 OUT"
mark 1.5 "SAMPLED" dash
mark 9 "CS# HIGH"
:::
```

:::signals SPI Mode 0, Command 0x9F (Read JEDEC ID)
signal "CS#" 1000000001
signal "SCLK" 0nnnnnnnn0
signal "MOSI" x========x "1,0,0,1,1,1,1,1"
signal "MISO" zzzzzzzzzz
mark 1 "CS# LOW, BIT 7 OUT"
mark 1.5 "SAMPLED" dash
mark 9 "CS# HIGH"
:::

### Budget gauges
Used against capacity, one gauge a line, hatched to the used fraction, with the figures and the percentage at the
end; hex is read as hex. `mark PERCENT "LABEL"` sets a limit across them all. A firmware image's memory:

```
:::budget Firmware 1.0 Memory
bar "RAM, static" 61200 73728 B
bar "Heap region" 301000 368640 B
bar "App image in flash slot" 412000 0x80000 B
bar "Bootloader" 9800 0x4000 B
:::
```

:::budget Firmware 1.0 Memory
bar "RAM, static" 61200 73728 B
bar "Heap region" 301000 368640 B
bar "App image in flash slot" 412000 0x80000 B
bar "Bootloader" 9800 0x4000 B
:::

### Pictures and columns
`![Caption](path){width=half}` takes an SVG, inlined so its lettering stays live, or a PNG; `width=third` and
`gray=1` (a dark screen capture, printed inverted as ink on paper) are the options. `::::row` sets its contents
side by side, columns split on a line `|||`, closed by `::::`; anything can go in a column.

::::row
```
![A Screen Capture](../kitchen-sink/screen.png){width=third gray=1}
```
|||
![A Dark Screen Capture, Printed as Ink](../kitchen-sink/screen.png){width=third gray=1}
::::

## Making a sheet

:::checklist Turn a Report into a Sheet | Writer
1  python sheet.py report.md --png
     -s section=N -s tab=XXX -s date=MM.DD.YYYY
2  read every page PNG; fix what crowds
3  add figures, equations, cautions, checklists
4  byline DRAFT; send to the fact checker
5  apply corrections; name the checker
6  commit; send the PDF
:::

For a sheet of your own, copy `template.md`: it has the front matter and one of each block, with comments
that do not print. Later changes go in `:::changed` with `change:` set in the front matter; the basic date stays.

:::caution
Chrome does not print into the page margins, so the gutter numbers, edge tab and change bars sit inside the
content box: keep `main`'s padding when restyling. A block closes at the first line of exactly its own colons, so a
block that holds blocks takes four (`::::changed` around `:::equations`), and a row's source cannot be shown in a row.
:::
