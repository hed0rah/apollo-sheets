---
title: "Memory Mechanisms"
section: "1"
tab: NEURO
handbook: Apollo Sheets
system: "NEURO -- memory mechanisms drawn from small specs"
doc: NR-1
rev: R1
status: Draft
mission: component kitchen sink
date: 11.14.2026
by: "Four interactive figures for how a brain remembers: cells competing for a memory, a network completing a cue, recall under reviews, and a cycle that switches between taking in and recalling."
abstract: "Each block reads a small JSON spec and draws a seeded, illustrative model of one mechanism. On the web the figures are live: drag, step, click. On paper each prints its settled state. The models show the shape of a mechanism; none is fitted to data, and each says so on the figure."
---

## What this is {#what}

:::table The blocks
| Block | Reads | Shows |
|---|---|---|
| `:::engram` | cells, events with times, an excitability time constant | which cells each memory takes, and how memories close in time share cells |
| `:::attractor` | a grid size, patterns as rows of `#` and `.`, a cue | a Hopfield network storing the patterns and completing the cue, and failing past capacity |
| `:::retention` | items with review days | recall over time under a power-law forgetting curve, and what each review adds |
| `:::rhythm` | phases in degrees, input streams with their peak phase | a cycle split into modes, with the inputs that dominate each |
:::

## Allocation {#engram}

:::engram Allocation by excitability: memories close in time share cells | src=engram.json
:::

## Completion {#attractor}

:::attractor Pattern completion in a Hopfield network | src=attractor.json
:::

## Retention {#retention}

:::retention Spacing: the same reviews, massed or spread | src=retention.json
:::

## Modes {#rhythm}

:::rhythm Encoding and retrieval on alternate halves of a theta cycle | src=rhythm.json
:::

## The formats {#formats}

:::table engram
| Field | What |
|---|---|
| `events[]` | `name`, `t` (in `unit`), optional `color` (pull, push, irq, ok, wait, crit) |
| `cells`, `k` | how many cells, and how many each memory takes |
| `tau`, `boost`, `noise` | excitability left by a memory and its time constant; the spread of baseline excitability |
| `drag`, `horizon`, `seed` | the event the slider moves; the time axis; the seed |
:::

:::table attractor
| Field | What |
|---|---|
| `w`, `h` | the grid (w*h at most 400) |
| `patterns[]` | `name`, `rows`: `h` strings of `w` characters, `#` on and `.` off |
| `cue` | `pattern`, `flip` (fraction of cells flipped), `mask` (top, bottom, left, right or none) |
:::

:::table retention
| Field | What |
|---|---|
| `items[]` | `name`, `reviews` (days), optional `s0` (initial stability in days) |
| `horizon`, `target`, `editable` | the time axis in days; the recall target line; the item a reader can edit |
:::

:::table rhythm
| Field | What |
|---|---|
| `phases[]` | `from`, `to` (degrees), `label`, optional `note` and `color` |
| `streams[]` | `name`, `peak` (degrees) |
| `period`, `start`, `marks[]` | the cycle's name; where the hand starts; points on the dial with a `label` |
:::
