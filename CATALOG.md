# APOLLO sheets: a catalog of figures

The visualization catalog for apollo-sheets, organized by the job a figure does. Each entry gives:
- what the figure is for and when to use it;
- the apollo-sheets block that draws it, or "not planned" with the reason and what to use instead;
- a minimal snippet that renders as written.

Every snippet here renders. `python catalog_check.py` puts them all on one sheet to prove it. The paths in
the snippets are relative to the repository root. `examples/apollo/apollo.md` shows each block at full size with real data.

APOLLO sheets are paper first: black ink, US Letter, read with a pen. Anything that moves, takes input or
recalculates belongs in an interactive page. A sheet carries the static half: the figure at its stated values, and
the table or formula behind it.

## Choosing, in one pass

Answer these questions in order and stop at the first yes:

1. Is it a place, a route or a region? Use **geography**.
2. Does it run over time or along a sequence? Use **time**.
3. Does something move from one stage to the next? Use **flow**.
4. Is it parts of a whole? Use **part of whole**.
5. Is it how values spread? Use **distribution**.
6. Is it how things connect or co-vary? Use **relationship**.
7. Is it what a thing is made of, or how it is laid out? Use **structure**.
8. Otherwise, use **compare**.

A table is the right answer more often than it looks. Draw a figure when the shape of the numbers is the point, and
set a table when the numbers themselves are.

---

## 1. Compare

Values set side by side across categories or things.

### Bar chart
**For:** a few categories, one value each. **Use when** the reader should rank them or see their gaps.
`:::bars`. Use `horizontal` for long names and `log` when the values span decades.
```
:::bars On-Chip SRAM, KB
horizontal
log
bar "ATmega328P" 2
bar "RP2040" 264
bar "ESP32" 520
:::
```

### Grouped bars
**For:** two or three series across the same categories. **Use when** every category has the same few measures.
`:::bars` with `series`. The series are told apart by hatch, with a key.
```
:::bars Median and P95, ms
series "P50" "P95"
bar "report A" 359 376
bar "report B" 214 239
:::
```

### Dot plot (lollipop)
**For:** many categories, or two values per category. **Use when** bars would be heavy, or when the gap between two
values matters more than their size. `:::bars` with `dots`.
```
:::bars Median and P95, ms
series "P50" "P95"
dots
horizontal
bar "report A" 359 376
bar "report B" 214 239
:::
```

### Slope chart
**For:** the same things at two times or under two conditions. **Use when** the change is the story.
`:::slope`.
```
:::slope Directory Sizes, KB
heads "before" "after"
item "sheets" 557 3077
item "viz" 2500 2500
:::
```

### Parallel coordinates
**For:** a few things measured on many quantities. **Use when** you would reach for a radar chart. Each quantity
gets its own axis. `:::parallel`, from `item` lines or `csv PATH NAMECOL COL ...`.
```
:::parallel Three Microcontrollers
axes "MHz" "SRAM, KB" "GPIO"
item "ATmega328P" 20 2 23
item "RP2040" 133 264 30
item "ESP32" 240 520 34
:::
```

### Gauge (bullet)
**For:** used against capacity: memory, power, link budgets. **Use when** the limit matters as much as the value.
`:::budget`. It reads hex, and `mark` draws a limit line.
```
:::budget Memory
bar "RAM" 69540 73728 B
bar "Flash" 451296 0x8DFBC B
mark 90 "RED AT 90 %"
:::
```

### Small multiples
**For:** the same small figure, one per condition. **Use when** one figure would be crowded. Use a `::::row` with
any number of columns, split on `|||`.
```
::::row
:::dist report A
hist examples/apollo/data/render-ms.csv ms where=sheet:report-a bins=10
size 2.2 1.6
:::
|||
:::dist report B
hist examples/apollo/data/render-ms.csv ms where=sheet:report-b bins=10
size 2.2 1.6
:::
::::
```

### Table with sparklines
**For:** numbers that each carry a trend. **Use when** the exact value and its direction both matter. Put
`[[spark 3 5 4 8]]` in a table cell or in prose.
```
:::table Render Time
| Sheet | Runs | Median |
|---|---|---|
| report A | [[spark 436 348 335 358 332 358]] | 359 ms |
:::
```

### Radar chart: not planned
Its area changes with the order of the axes, and its angles are hard to compare in ink. Use parallel coordinates
or small multiples instead.

---

## 2. Distribution

How values spread: the middle, the width, the tails, the outliers.

### Histogram
**For:** the shape of one set of values. **Use when** you need to show where the values pile up. Use `:::dist` with
`hist`, and `mark` for a percentile.
```
:::dist Render Time
hist examples/apollo/data/render-ms.csv ms bins=24
unit "ms"
mark 371 "P95"
:::
```

### Box plot
**For:** several sets compared by their quartiles. **Use when** you have a few sets and want the middle and the
spread. Use `:::dist`, with `box` (five numbers) or `data` (raw values from a CSV).
```
:::dist Latency
box "service A" 12 18 22 30 51 64
box "service B" 9 11 13 16 24
unit "ms"
:::
```

### Violin
**For:** box plots that also show the shape. **Use when** a set is bimodal or skewed and a box would hide it. Use
`:::dist` with `data` and `violin`.
```
:::dist By Sheet
data "report A" examples/apollo/data/render-ms.csv ms where=sheet:report-a
data "report B" examples/apollo/data/render-ms.csv ms where=sheet:report-b
violin
unit "ms"
:::
```

### Strip (every value)
**For:** small sets where every point counts. **Use when** you have fewer than a few hundred values. Use `:::dist`
with `strip`; the dots sit over the boxes.
```
:::dist Every Run
data "report A" examples/apollo/data/render-ms.csv ms where=sheet:report-a
strip
unit "ms"
:::
```

### Cumulative curve (ECDF)
**For:** reading any percentile straight off the chart. **Use when** the reader asks "what share is under X?" (p50,
p95, p99). Use `:::dist` with `ecdf`.
```
:::dist Cumulative
data "report A" examples/apollo/data/render-ms.csv ms where=sheet:report-a
data "report B" examples/apollo/data/render-ms.csv ms where=sheet:report-b
ecdf
unit "ms"
:::
```

### Error bars
**For:** measurements that carry their uncertainty. **Use when** each point is a mean of repeats. Use `:::plot`
with `err=COLUMN` on a `y` series.
```
:::plot Time against Points
csv examples/apollo/data/plot-ms.csv
x points "points"
y ms "MEAN" dots err=sd
log x
:::
```

### Density curve
A violin is two density curves back to back. For one curve, use a histogram with more bins.

---

## 3. Part of whole

Shares that add up to something.

### Stacked and 100 % bars
**For:** each category's parts. **Use when** both the parts and the totals matter. Use `:::bars` with `stacked`,
or `percent` when only the shares matter.
```
:::bars Bytes by Kind
series "Figures" "Code" "Text"
percent
horizontal
bar "sheets" 2422 86 43
bar "viz" 2489 49 22
:::
```

### Stacked area
**For:** parts of a whole over time. Use `:::plot` with `area` on each series, and `percent` to make each band a
share.
```
:::plot Commits by Area
csv examples/apollo/data/commits.csv
x day "day"
y other "OTHER" area
y notes "NOTES" area
y sheets "SHEETS" area
:::
```

### Treemap
**For:** nested shares, such as disk use or a budget by department. **Use when** the parts form a hierarchy. Use
`:::treemap`: an indented outline, with each leaf ending in its value.
```
:::treemap Disk, KB
sheets
  pdf 2255
  py 79
viz
  png 1200
  pdf 1022
:::
```

### Waffle
**For:** a few shares, read as counts out of 100. **Use when** you would reach for a pie. `:::waffle`.
```
:::waffle Files by Kind
part "Figures" 30
part "Code" 24
part "Text" 14
:::
```

### Waterfall
**For:** a running total built from rises and falls: a budget, a cash flow, a loss budget. `:::waterfall`.
```
:::waterfall Link Budget, dB
start "TX power" 20
step "Cable" -2
step "Antennas" 6
step "Path loss" -110
total "At RX"
:::
```

### Pie and donut: not planned
Readers judge angles poorly, and slices are hard to tell apart in ink. Use a waffle, 100 % bars, or a table.

### Sunburst: not planned
Its outer rings distort the shares. Use a treemap.

### Marimekko (mosaic): not planned
Two shares at once crowd a page in ink. Use a 100 % bar chart with the totals in a table beside it.

---

## 4. Flow

Things moving through stages, decisions and hand-offs.

### Flowchart and decision tree
**For:** steps with branches: troubleshooting, procedures. Use `:::diagram` with `diamond` nodes. A `bend=` edge
gives a back-edge.
```
:::diagram Troubleshooting
node err "ERROR 404" 0 0 round
node dns "DNS OK?" 1 0 diamond w=0.8 h=1.0
node fix "FIX DNS" 2 0
node rst "RESTART" 1 1
edge err dns
edge dns fix "NO"
edge dns rst "YES"
:::
```

### State machine
**For:** the states something can be in, and the moves between them. Use `:::diagram` with `round` nodes, `bend=`
for a pair of opposite moves, and `loop` for a self-transition.
```
:::diagram Order States
node p "PENDING" 0 0 round
node s "SHIPPED" 1 0 round
node d "DELIVERED" 2 0 round
edge p s "SHIP"
edge s p "RETURN" bend=0.5
edge s d "ARRIVE"
loop p "RETRY"
:::
```

### Swimlane
**For:** a process where it matters who does each step. Use `:::diagram` with a `lane "OWNER" ROW` for each row.
```
:::diagram Review
lane "AUTHOR" 0
lane "REVIEWER" 1
node w "WRITE" 0 0 round
node r "REVIEW" 1 1
node m "MERGE" 2 0 round
edge w r
edge r m "OK"
:::
```

### Sequence diagram
**For:** messages between actors over time: handshakes, API calls. `:::sequence`, with `dash` for a reply and
`gap` where time passes.
```
:::sequence Login
actor c "CLIENT"
actor s "SERVER"
msg c s "POST /LOGIN"
msg s s "CHECK"
msg s c "TOKEN" dash
:::
```

### Pipeline (DAG)
**For:** dependent stages: CI, ETL, build steps. Use `:::diagram` laid out on a grid, with `fence` to group
stages. For a graph with no natural grid, use a network.
```
:::diagram Build
node src "SOURCE" 0 0 round
node test "TEST" 1 0
node lint "LINT" 1 1
node pkg "PACKAGE" 2 0
edge src test
edge src lint
edge test pkg
edge lint pkg
fence "CI" test lint
:::
```

### Sankey
**For:** quantities moving between stages: energy, money, traffic. `:::sankey`. Each ribbon is as wide as its value.
```
:::sankey Budget, k
unit "k"
flow "Income" "Rent" 18
flow "Income" "Food" 9
flow "Income" "Savings" 6
:::
```

### Funnel
**For:** stages that narrow: conversion, recruitment, filtering. `:::funnel`. Each stage shows its share of the
first.
```
:::funnel Sign-ups
stage "visited" 1000
stage "signed up" 180
stage "paid" 40
:::
```

### Chord diagram: not planned
Its crossing ribbons need colour to read. Use a Sankey (for direction) or a shaded matrix.

---

## 5. Relationship

How things connect, overlap or move together.

### Scatter and bubble
**For:** two quantities against each other. Add `size=` for a third quantity and `fit` for the trend line and its r.
`:::scatter`.
```
:::scatter Clock and SRAM
xlabel "MHz"
ylabel "SRAM, KB"
log y
fit
point 20 2 "ATmega328P"
point 133 264 "RP2040" size=2
point 240 520 "ESP32" size=2
:::
```

### Heatmap and correlation matrix
**For:** a grid of values, such as hour by day or x by y. `:::matrix` with `shade`. A calendar heatmap is the
same block, with weeks as rows and days as columns.
```
:::matrix Commits by Hour
shade
cols "00-08" "08-16" "16-24"
row "Mon" 0 9 8
row "Tue" 0 3 0
:::
```

### Feature matrix
**For:** yes, partly and no across items: feature comparisons, permissions. `:::matrix` with `yes`, `part`, `no`
and `-`.
```
:::matrix Features
cols "Wi-Fi" "USB" "Two cores"
row "RP2040" no yes yes
row "ESP32" yes no yes
row "STM32F103" no part no
:::
```

### Entity relationship
**For:** tables and how their rows relate. Use `:::diagram` with `ends=1:N` on the edges.
```
:::diagram Orders
node c "CUSTOMER" 0 0
node o "ORDER" 1 0
node i "ITEM" 2 0
edge c o "PLACES" ends=1:N
edge o i "HOLDS" ends=1:N
:::
```

### Network graph
**For:** a graph with no natural rows: dependencies, a mesh, who talks to whom. `:::network` lays it out with a
deterministic spring model, or `layout circle`.
```
:::network Imports
link app lib arrow
link app yaml arrow
link lib numpy arrow
:::
```

### Venn diagram
**For:** overlap between two or three groups. `:::venn`. The regions are A, B, AB and so on, plus `out`.
```
:::venn Features
set "Wi-Fi" "Native USB"
in A "ESP32"
in B "RP2040"
in out "ATmega328P"
:::
```

### 2 by 2 quadrant
**For:** two judgements at once: effort and value, likelihood and impact. `:::quadrant`.
```
:::quadrant Priorities
x "low effort" "high effort"
y "low value" "high value"
name 2 "Do first"
name 4 "Skip"
point 0.2 0.8 "bars"
point 0.8 0.2 "exploded view"
:::
```

---

## 6. Time

Order, duration and change.

### Line chart (time series, functions)
**For:** a quantity over time, or y as a function of x. Use `:::plot`, with `y` for data from a CSV and `fn` for an
exact curve. `panel` stacks panels on one x axis; `hline` and `mark` draw limits and events.
```
:::plot First-Order Low-Pass
range 0.01 100
log x
fn "-10*log10(1+x**2)" "GAIN"
hline -3.01 "-3 DB"
panel
fn "-degrees(arctan(x))" "PHASE"
:::
```

### Timeline and Gantt chart
**For:** phases, a schedule, a mission. Use `:::timeline` with `bar`. Add `milestone` for dates that have no length
and `after` for dependencies.
```
:::timeline Release
axis "weeks" 0 6 ticks=1
bar "Build" 0 2 hatch
bar "Test" 2 4 open
milestone "Test" 4 "FREEZE"
bar "Ship" 4 5 hatch
after "Build" "Test"
after "Test" "Ship"
:::
```

### Timing diagram
**For:** digital signals on a clock: SPI, I2C, handshakes. `:::signals`.
```
:::signals SPI Byte
signal "CS#" 1000000001
signal "SCLK" 0nnnnnnnn0
signal "MOSI" x========x "1,0,0,1,1,1,1,1"
:::
```

### Sparkline
**For:** a trend at word size, inside prose or a table: `[[spark 3 5 4 8]]`. It is listed under compare, as a
table with sparklines.

### Bump chart: not planned
For rank over many times, use small multiples or a slope chart for each pair of times. A bump chart's crossing
lines need colour to read.

---

## 7. Structure

What a thing is made of, and how it is laid out.

### Block diagram and architecture
**For:** components and what feeds what: hardware subsystems, services, cloud layouts. Use `:::diagram`, with
`fence` for subsystems, `drum` for storage, and `dash` for optional parts.
```
:::diagram Sensor Node
node s "SENSOR" 0 0
node m "MCU" 1 0
node f "FLASH" 1 1 drum
node r "RADIO" 2 0
edge s m "I2C"
edge m f "SPI" both
edge m r "UART"
fence "BOARD" s m f
:::
```

### Tree and org chart
**For:** a hierarchy: ownership, files, inheritance, reporting lines. Use `:::tree`, written as an indented
outline; `down` on the first line puts the root at the top.
```
:::tree Ownership
Deployment
  ReplicaSet
    Pod
    Pod
:::
```

### Layer stack and memory map
**For:** layers: a protocol stack, memory tiers, an address map. Use `:::stack`, with `at=` for addresses and
`span` for brackets.
```
:::stack Address Map
layer "ROM" "16 KB" at=0x00000000
layer "SRAM" "264 KB" hatch at=0x20000000
layer "Peripherals" at=0x40000000
:::
```

### Register and packet layout
**For:** the bits of a register or a protocol header. Use `:::bits`: `numbers up` as in RFCs, `hatch` for
reserved bits.
```
:::bits Status Register
width 8
field "EN" 1
field "MODE" 2
field "RSVD" 3 hatch
field "IRQ" 2
:::
```

### Annotated picture (callouts)
**For:** the parts of a thing you can photograph or screenshot. It is also the practical stand-in for an exploded
view. Use `:::callouts` on a PNG, with `gray` for a dark screen.
```
:::callouts Screen
image examples/kitchen-sink/screen.png gray
at 0.33 0.22 "program"
at 0.03 0.69 "register 1"
:::
```

### Exploded view and assembly drawing: not planned
These come from CAD or a drawing, not from text. Render the views in CAD, then name the parts with callouts.

### Mind map and radial tree: not planned
A tree reads the same hierarchy more clearly. A radial layout would take about 40 lines in handbook.py if a real
sheet ever needs one.

---

## 8. Geography and fields

Places, regions, and quantities spread over a plane.

### Point and route map
**For:** where things are and the paths between them: stations, tracks, field sites. Use `:::map` with layers
(GeoJSON or a shapefile), `point`, `route`, `graticule` and `scale`.
```
:::map Track
layer examples/apollo/data/pacific-land.geojson line
extent -180 -150 4 28
route -169.15 13.32 -157.95 21.35 "ROUTE" dash
point -169.15 13.32 "START" star
graticule 5
scale 300
:::
```

### Zone and area map
**For:** a region with a boundary: a forecast cone, a coverage area, a service zone. Use `:::map` with the layer
set to `hatch`.
```
:::map Zone
layer examples/apollo/data/pacific-land.geojson hatch
extent -162 -154 18 23
:::
```

### Choropleth
**For:** a value for each region: population, rainfall, load. Use `:::map` with `key=PROPERTY` on the layer and a
`value` line for each region. Values print light to dark, with a scale.
```
:::map Statehood
layer examples/apollo/data/us-states.geojson key=name
value "California" 1850
value "Texas" 1845
value "Utah" 1896
value "Kansas" 1861
:::
```

### Contour (isolines)
**For:** a field f(x, y) as lines of equal value: potential, elevation, pressure. Use `:::contour` with an exact
`fn` in x and y.
```
:::contour Charge Pair
fn "1/hypot(x-1,y) - 1/hypot(x+1,y)"
range -3 3 -2 2
levels -1 -0.5 0.5 1
:::
```

### Raster (grid, spectrogram, image)
**For:** a dense grid of values, set as gray with a scale: a waterfall from the SDR, a heat field, an image. Use
`:::raster`, with `csv` (a grid with no header) or `fn`.
```
:::raster Field
fn "exp(-(x**2+y**2))"
extent -2 2 -2 2
unit "intensity"
:::
```

### Polar plot and wind rose
**For:** values by direction: antenna patterns, winds, bearings. Use `:::polar` with `fn` for r(t), or `rose` lines
for a wind rose (north up, clockwise).
```
:::polar Wind
rose N 12
rose NE 7
rose E 3
rose S 5
rose W 9
:::
```

### Flow map
For routes with their volumes, use `:::map` `route` lines and put the volumes in the labels. Ribbon widths on a
map are not planned.

### Vector field (arrows)
**For:** flow and force over a plane: wind, current, a field down a potential. Use `:::contour` with `arrows N`:
the field (minus the gradient of f) on an N by N grid, over the contour lines.
```
:::contour Field Lines
fn "1/hypot(x-1,y) - 1/hypot(x+1,y)"
range -3 3 -2 2
levels -1 -0.5 0.5 1
arrows 12
:::
```

### Cartogram: not planned
It distorts geography on purpose and needs a projection solver. Use a choropleth.

---

## Around the figures

The prose blocks, for completeness:

| Need | Block |
|---|---|
| numbered paragraphs | `##`, `###`, `####` |
| a table, numbered | `:::table Caption` around a pipe table |
| an equation, numbered | `$$ ... $$`; `:::equations` to align several; `:::symbols` for the "where" list |
| inline math | `$x^2$` |
| a procedure | `:::checklist TITLE \| ROLE` |
| a warning to the reader | `:::caution`, `:::warning`, `:::note` |
| what changed after the basic date | `:::changed` (`::::changed` when it holds blocks), with `change:` in the front matter |
| a picture | `![Caption](path){width=half gray=1}` |
| side by side | `::::row` ... `\|\|\|` ... `::::` |

## Interactive widgets

The original catalog's section 6 (budget planner, portfolio donut, cash-flow Sankey with sliders, simulation,
checklist with saved state) describes interactive pages, not sheets. Each has a printed half here: `:::budget` or
`:::waterfall` for the planner; `:::waffle` or 100 % bars for the portfolio; `:::sankey` for the cash flow;
`:::plot` with `fn` plus a table for the simulation; `:::checklist` for the checklist. The live versions belong in
an interactive house style.
