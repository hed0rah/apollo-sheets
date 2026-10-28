---
title: Subject of the sheet
section: "1"
tab: XXX
handbook: Operations Handbook
system: SUBJECT -- one line on what it is
doc: XXX-1
mission: project or build it covers
date: MM.DD.YYYY
by: "Review sheet for WHO, from WHOSE report. DRAFT until checked."
---

<!--
A new APOLLO sheet: copy this file next to its figures and render it with
  python sheets/sheet.py this.md --png
Comments like this one never print. Keep the order below: description, data, procedures, cautions, findings.
examples/apollo/apollo.md shows every block with its source; examples/rc-filter and examples/lander are finished sheets.
-->

## Functional description

What it is and what it does, for a reader who has not seen it. One idea a paragraph.

:::diagram Subject Functional Diagram
node in "INPUT" 0 0 round
node core "THE THING" 1 0
node store "STORAGE" 1 1 drum
node out "OUTPUT" 2 0 round
edge in core
edge core store "WRITES" both
edge core out
:::

## Theory of operation

<!-- the governing equations, numbered, with a where-list; inline math like $x^2$ in the prose -->

$$ y = f(x) $$

:::symbols
x | what x is | unit
y | what y is | unit
:::

:::equations
a = b + c
= 2 + 3
:::

## Performance and design data

:::table Subject Data
| Parameter | Value | Source |
|---|---|---|
| Something | 1 unit | file:line or who checked it |
:::

:::plot Response
range 0.1 10
fn "1/sqrt(1+x**2)" "MODEL"
log x
xlabel "x"
ylabel "y"
hline 0.707 "-3 DB"
:::

:::budget Resources
bar "RAM" 100 128 KB
bar "FLASH" 300 512 KB
:::

<!-- also: :::timeline :::sequence :::signals :::stack :::bits :::bars :::matrix :::tree :::callouts,
     plot panels, diagram diamonds / bend= / loop, images with {width=half|third gray=1}, ::::row with |||;
     examples/apollo/apollo.md shows each beside its source -->

## Procedures

:::checklist Do the Thing | Operator
1  first step
2  second step
     detail, indented
:::

## Cautions

:::caution
Costs time or data if ignored.
:::

:::warning
Damages hardware or loses work for good if ignored.
:::

## Review findings

1. A finding, with where it is (file:line) and what would fix it.

<!-- after the basic date: set change: MM.DD.YYYY above and wrap altered text in :::changed ... :::
     (::::changed ... :::: when it holds other ::: blocks) -->
