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

## Images

Any SVG or PNG. Width may be half or third; gray=1 prints a dark screen capture as ink on paper.

::::row
![A screen capture, as captured](screen.png){width=half}
|||
![The same capture with gray=1](screen.png){width=half gray=1}
::::
