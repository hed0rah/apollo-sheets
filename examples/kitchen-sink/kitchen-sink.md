---
title: Kitchen sink
section: "1"
tab: KIT
handbook: Operations Handbook
system: Every block apollo-sheets knows
doc: KIT-1
mission: EXAMPLE-1
date: 10.27.2026
change: 10.27.2026
by: one of everything, with the Markdown that draws it in the README
---

## Text

Plain Markdown paragraphs justify in the Roman face. **Bold**, *italic*, _underline_, `typewriter`, H~2~O and
10^6^ all work inline, and a spaced double hyphen -- like this -- prints as an en dash. Links keep their words
and drop the URL, because paper has no links: [see the README](https://example.com).

Inline math sits in the line: the time constant is $\tau = RC$ and the corner is $f_c = 1/(2\pi RC)$.

$$\boxed{v(t) = V_0 \, e^{-t/\tau}}$$

### Lists and code

- an unordered list item
- a second one, which wraps onto a following line when it runs long enough to need
  more than one line of the sheet
- a third

1. an ordered list
2. numbers itself

```
V16 N68 E      monitor range, altitude rate, altitude
V57 E          landing radar update permitted
```

---

## Tables

A bare pipe table renders ruled and untitled. Wrap it in a table block to number and title it.

| Mode | Gain | Rate |
|---|---|---|
| coarse | 4.0 | 2.0 deg/s |
| fine | 0.5 | 0.2 deg/s |

:::table Thruster Quad Assignments
| Quad | Axis | Thrusters | Min impulse |
|---|---|---|---|
| A | pitch, roll | A1U A2D A3A A4F | 0.4 N s |
| B | yaw, roll | B1L B2R B3A B4F | 0.4 N s |
| C | pitch, roll | C1U C2D C3A C4F | 0.4 N s |
| D | yaw, roll | D1L D2R D3A D4F | 0.4 N s |
:::

## Call-outs

:::note
A note is advice: nothing breaks if it is ignored.
:::

:::caution
A caution protects the equipment. Do not command fine mode with a quad isolated.
:::

:::warning
A warning protects the crew. It is boxed so it cannot be missed.
:::

:::changed
### Change bars

Anything inside a changed block gets a black bar in the left gutter, the handbook's way of saying "this
paragraph is new since the last issue".
:::

:::checklist Quad isolation | CDR
QUAD A ISOL VLV ......... CLOSE
  verify talkback ....... BARBERPOLE
RCS SYS A/B ............. CHECK PRESS
ATT CONTROL ............. MODE CONT
:::

# Figures

## Block diagrams

Nodes sit on a grid of columns and rows. Shapes: box, round, drum (storage), dash (outside the system) and text
(lettering only). A fence draws a dashed boundary round a subsystem; edges may be dashed, two-headed and labelled.

:::diagram Attitude Control Functional Diagram, Every Shape and Edge
grid 1.8 0.8
node imu "inertial\nmeasurement" 0 0
node gnc "guidance\ncomputer" 1 0 round
node jets "jet select\nlogic" 2 0
node rcs "reaction\ncontrol jets" 3 0
node ground "ground\nuplink" 0 1 text
node mem "erasable\nmemory" 1 1 drum
node crew "crew\ndisplays" 2 1 dash
fence "primary guidance" gnc mem
edge imu gnc "attitude"
edge gnc mem both
edge gnc jets "rate cmd"
edge jets rcs
edge jets crew "jet status" dash
edge ground mem "state vector" dash
note 3 1 "four quads,\nsixteen jets"
:::

## Graphs

A diagram is also a graph: a diamond is a decision, `bend=` curves a back-edge, and a loop returns a node to
itself.

:::diagram Attitude Hold, a Decision Loop
grid 1.6 0.9
node sense "sense\nattitude" 0 0 round
node err "error\npast band?" 1 0 diamond w=0.8 h=1.1
node fire "fire\njets" 2 0
node coast "coast" 1 1 dash
edge sense err
edge err fire "YES"
edge err coast "NO" dash
edge fire sense "NEXT CYCLE" bend=0.4
edge coast sense "NEXT CYCLE" bend=-0.3
loop fire "PULSE TRAIN" top
:::

## Timelines

Bars may be hatched, open or solid; marks are vertical lines with a label above, and a call drops a leader from a
bar to lettering below the axis.

:::timeline Sequence of Events, Every Bar and Mark
axis "seconds" 0 60 ticks=10
bar ullage 0 7 solid
bar "main engine" 7 52 open "throttle 100 to 60 %"
bar "radar" 0 20 hatch
bar "radar" 20 60 open "lock"
bar "crew" 30 60 open
mark 7 "IGNITION"
mark 52 "CUTOFF" dash
call crew 35 "takeover"
:::

## Plots

Lines come from a CSV and are labelled at their right ends instead of with a legend; marks draw a vertical line.
Log axes are a single line.

::::row
:::plot Decay of Three Time Constants
csv decay.csv
x t "seconds"
y a "tau 2"
y b "tau 4"
y c "tau 8"
ylabel "percent"
mark 2 "tau"
:::
|||
:::plot The Same, on a Log Axis
csv decay.csv
x t "seconds"
y a "tau 2"
y b "tau 4"
y c "tau 8"
ylabel "percent"
log y
:::
::::

## Panels

A panel line starts a second panel under the first, on the same x; fn takes degrees() and radians().

:::plot Rate Loop, Gain and Phase
size 3.4 1.6
range 0.1 10
log x
fn "-10*log10((1-x**2)**2+(0.6*x)**2)"
ylabel "gain, dB"
mark 1 "NATURAL FREQUENCY"
panel
fn "-degrees(arctan2(0.6*x, 1-x**2))"
ylabel "phase, deg"
ylim -185 5
hline -90 "-90 DEG"
xlabel "w / wn"
:::

## Stacks and bit fields

A stack sets layers top to bottom; a bit field wraps fields into rows of bits, hatching the reserved ones.

:::stack Flight Software Layers
layer "Mission programs" "P00 TO P99"
layer "Interpreter" "VECTOR AND MATRIX OPS"
layer "Executive" "JOBS AND WAITLIST" hatch
layer "Hardware" "COUNTERS, CHANNELS" dash
span 2 3 "SYSTEM"
:::

:::bits Jet Command Word
width 16
field "Quad" 2
field "Jet" 2
field "Reserved" 4 hatch
field "Pulse width" 8
:::

## Bars and matrices

::::row
:::bars Firings by Quad
series "Rotation" "Translation"
unit "firings"
bar "A" 42 12
bar "B" 37 9
bar "C" 39 14
bar "D" 33 11
:::
|||
:::matrix Quad Authority
cols "Pitch" "Yaw" "Roll" "Translation"
row "Quad A" yes no yes part
row "Quad B" no yes yes part
row "Quad C" yes no yes part
row "Quad D" no yes yes part
:::
::::

With shade, a matrix of numbers is a heatmap: each cell tinted by its value.

:::matrix Jet Firings by Quad and Phase
shade
cols "Ullage" "Coast" "Braking" "Approach" "Landing"
row "Quad A" 4 2 9 14 21
row "Quad B" 4 1 7 12 18
row "Quad C" 4 2 8 15 20
row "Quad D" 4 1 6 11 17
:::

## Points and spreads

A scatter letters its points and fits a line; a dist draws boxes from five numbers (or raw CSV values).

::::row
:::scatter Pulse Width and Impulse
xlabel "pulse width, ms"
ylabel "impulse, N s"
fit
point 14 0.41 "MIN"
point 25 0.78
point 50 1.62
point 100 3.30
point 200 6.71 "LONG"
:::
|||
:::dist Jet Response by Quad
box "A" 18 21 22 24 27
box "B" 19 22 23 25 29 33
box "C" 17 20 22 23 26
box "D" 20 23 25 27 31
unit "ms"
mark 30 "LIMIT"
:::
::::

## Flows

A sankey draws flows between stages as ribbons as wide as their values.

:::sankey Propellant Budget, kg
unit "kg"
size 4.2 2.0
flow "system A" "attitude" 70
flow "system A" "translation" 45
flow "system A" "reserve" 25
flow "system B" "attitude" 65
flow "system B" "translation" 50
flow "system B" "reserve" 25
:::

## Images and callouts

Any SVG or PNG. Width may be half or third; gray=1 prints a dark screen capture as ink on paper. A callouts
block draws leaders from points on a picture to lettering in its margins, on the nearer side.

::::row
![A screen capture, as captured](screen.png){width=half}
|||
![The same capture with gray=1](screen.png){width=half gray=1}
::::

:::callouts The Display, Named
image screen.png gray
at 0.33 0.22 "program number"
at 0.15 0.52 "verb"
at 0.53 0.45 "noun"
at 0.03 0.69 "register 1"
at 0.36 0.78 "register 2"
at 0.64 0.69 "register 3"
:::

## Trees

:::tree Reaction Control, by System
RCS
  System A
    Quad A
    Quad C
  System B
    Quad B
    Quad D
  Ground test [dash]
:::

## Shares and choices

A quadrant places items on two judgements; a Venn letters overlaps; a treemap nests shares; a funnel narrows.

::::row
:::quadrant Anomalies to Work
x "rare" "frequent"
y "minor" "severe"
name 1 "Fix now"
name 2 "Plan for"
name 3 "Log"
name 4 "Work round"
point 0.2 0.8 "radar dropout"
point 0.75 0.75 "jet leak"
point 0.8 0.25 "display flicker"
point 0.3 0.2 "clock drift"
:::
|||
:::venn Jets by Duty
set "Pitch" "Yaw" "Roll"
in AC "quads A, C"
in BC "quads B, D"
:::
::::

:::treemap Flight Software by Module, Words
guidance
  navigation 6200
  targeting 3100
  steering 2400
control
  attitude 4100
  thrust 1800
executive
  jobs 1500
  waitlist 700
displays
  verbs 1900
  nouns 1200
:::

:::funnel Pre-Flight Checks
unit "checks"
stage "planned" 120
stage "run" 112
stage "passed" 104
stage "signed off" 98
:::
