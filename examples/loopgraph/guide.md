---
title: "Building an Interactive Technical Document"
section: "1"
tab: GUIDE
handbook: Apollo Sheets
system: "A GUIDE FOR A CODING AGENT -- one self-contained HTML page, with agent graphs that replay"
doc: LG-GUIDE-1
rev: R1
status: Draft
mission: how to build the doc
date: 11.10.2026
by: "For a coding agent asked to document a system, an agent graph or a protocol as an interactive page: the file shape, the components, the graph data format, the rules, and the checks before it ships."
abstract: "Write the document as Markdown with fenced ::: blocks; one command renders it into a single self-contained HTML page with a contents rail, numbered sections and figures, cross-references, light and dark, and figures that move: a trace scrubber, and agent loops replayed from JSON. A second route builds the same page by hand from the HTML template for when the renderer is not available."
---

## What you are making {#making}

One HTML file a reader opens offline. It has a contents rail on the left that tracks the reader, numbered sections,
numbered figures and tables with captions, links between them, a light and a dark theme, and figures you can play.
Nothing loads from the network. It prints.

Two routes produce it:

:::table The two routes
| Route | You write | You run | Use when |
|---|---|---|---|
| **A. Markdown** (preferred) | `doc.md`: front matter, `##` sections, `:::` blocks | `python web.py doc.md` | the renderer (`web.py`, beside `sheet.py`) is available |
| **B. By hand** | `doc.html` from the template, figures as JSON files | `python loopgraph/inline.py doc.html -o out.html` | it is not, or the page needs a layout the renderer does not do |
:::

Route A also gives you the printed edition for free: `python sheet.py doc.md` renders the same source as a PDF, every
interactive figure drawn at rest in black ink.

## Route A: the file shape {#shape}

```markdown
---
title: "What the System Is"
section: "1"
doc: ABC-1
rev: R1
status: Draft
date: 11.10.2026
by: "One sentence: who this is for and what it covers."
abstract: "Three or four sentences. The reader who stops here should know the answer."
---

## The first section {#first status=built}

Prose. A link to [the loop](#fig-1.2) or [a section](#second) becomes a cross-reference.

:::loop The agent loop, replayed. | src=graphs/agent.json
:::

## The second section {#second}
```

- `##` is a numbered section; `{#anchor}` names it for links; `status=built|prototyped|designed|speculative` puts a
  pill on it and a dot in the rail. `#` with a `:::part` groups sections into parts.
- Figures and tables are numbered by section (`Fig. 2.3`) and listed in the rail. Link to one with `#fig-2.3`.
- Every `:::` block takes its caption after the name and ends at a line of `:::` alone.

## Route A: the components {#components}

Pick the figure by what the reader needs to see, not by what looks good.

:::table Which block for which job
| Block | Shows | Write it as |
|---|---|---|
| `:::loop` | an agent graph with state: loops and their bounds, conditions, human gates, checkpoints, a run replayed | a JSON file, `src=`, or the JSON as the body |
| `:::diagram` | a system map or a general flow, no state, no loop counters | `grid`, `node`, `edge` lines, nodes placed on a grid |
| `:::trace` | events in time, scrubbed one by one | `step "label" \| what happened \| #anchor` lines |
| `:::sequence` | messages between parties | the block's own line format |
| `:::stack`, `:::tree`, `:::matrix` | layers, a hierarchy, a grid of relations | the block's own line format |
| `:::table` | anything tabular | a Markdown table as the body |
| `:::checklist` | a procedure to follow, in order | `1 text` lines; `Title \| role` as the caption |
| `:::note`, `:::caution`, `:::warning` | a callout, from aside to must-read | Markdown as the body |
| `:::glossary` | terms; the first use of each in the text gets a hover card | `term: definition` lines |
| `::::row` | blocks side by side | blocks separated by a `\|\|\|` line |
:::

A code block is a fenced block as usual. Do not draw diagrams in a code block with spaces and pipes: they break at
the first change and mean nothing to a screen reader. Every picture is a figure block.

## The agent loop figure {#loop}

The `:::loop` block takes one JSON object. It is laid out automatically, so you never place a node: give it the
graph you have.

```json
{
  "title": "Answer with tools",
  "dir": "LR",
  "limits": {"recursion_limit": 25},
  "state": {
    "messages": {"reducer": "append", "doc": "the conversation"},
    "calls":    {"reducer": "sum"}
  },
  "nodes": [
    {"id": "start", "kind": "start"},
    {"id": "agent", "kind": "llm", "label": "agent", "sub": "plan or call", "writes": ["messages"]},
    {"id": "route", "kind": "router", "label": "tool calls?"},
    {"id": "tools", "kind": "tool", "label": "tools", "writes": ["messages", "calls"]},
    {"id": "end", "kind": "end"}
  ],
  "edges": [
    {"from": "start", "to": "agent"},
    {"from": "agent", "to": "route"},
    {"from": "route", "to": "tools", "kind": "cond", "when": "yes"},
    {"from": "tools", "to": "agent", "kind": "loop", "max": 5, "counter": "calls"},
    {"from": "route", "to": "end", "kind": "cond", "when": "no"}
  ],
  "run": [
    {"node": "start", "writes": {"messages": "user: question"}},
    {"node": "agent", "writes": {"messages": "ai: call search"}},
    {"node": "route"},
    {"node": "tools", "writes": {"messages": "tool: 3 results", "calls": 1}, "checkpoint": "c1"},
    {"node": "agent", "writes": {"messages": "ai: the answer"}},
    {"node": "route"},
    {"node": "end", "via": "route"}
  ]
}
```

:::table Node and edge kinds
| Node kind | For | Edge kind | For |
|---|---|---|---|
| `start`, `end` | entry and exit | `next` | the default |
| `llm` | a model call | `cond` | a conditional edge; needs `when` |
| `tool` | runs tools or commands | `loop` | a back edge; `max` and `counter` if bounded |
| `router` | a pure decision on state | `fail` | an error path; a `label` |
| `human` | an approval; `interrupt: before` or `after` | `resume` | a human's answer continuing the run |
| `step` | plain code | `send` | fan-out to parallel copies |
| `store` | a write or read of git, a file, a database | | |
| `fail` | an error exit | | |
:::

The rest of the fields:

- `groups: [{id, label, collapsed}]` and `group` on a node make a subgraph the reader can collapse. One level.
- `reducer` is `replace`, `append`, `sum` or `merge`; a run step's `writes` gives the new value, the one new item, the
  increment, or the fields to merge.
- `limits` takes a number or `{max, of}`, where `of` names the state key or loop counter it bounds. `recursion_limit`
  counts steps. Any other limit that bounds nothing in the run shows as a fixed setting.
- `pause` on a run step stops playback there until the reader presses resume; put it on the step at a human node.
- `checkpoint` on a run step marks it; the reader can jump back to any checkpoint and see the state it holds.
- `via` on a run step names the node it came from, when the step before it was not that node (parallel branches).
- `doc` on any node, edge or group is the hover card's text: say where in the code it lives.

### Exporting a graph from code {#export}

Do not hand-write a graph that exists in code; export it. For a LangGraph graph the shape is below. It is a sketch:
check the attribute names against the version installed before you rely on it.

```python
g = app.get_graph()                       # the compiled graph's drawable view
nodes = [{"id": n.id, "kind": "start" if n.id == "__start__" else "end" if n.id == "__end__" else "step",
          "label": n.name} for n in g.nodes.values()]
edges = [{"from": e.source, "to": e.target, "kind": "cond" if e.conditional else "next",
          **({"when": str(e.data)} if e.data else {})} for e in g.edges]
# then, by hand: set each node's kind (llm, tool, router, human), mark back edges as loop with their bound,
# and add the state schema's keys with their reducers.
```

A run comes from the same graph: stream it with per-node updates and write one `run` step per update, or walk the
checkpointer's state history for the `checkpoint` ids. Keep a recorded run to 8 to 30 steps; trim a long one to
the passage that shows the point.

## Route B: by hand {#by-hand}

Start from the Interactive Whitepaper template (`web-template.html`, beside `web.py`): keep its `<head>`, its styles and its script
byte for byte, and replace the content inside `<main>`. Add the loop component by reference while you work:

```html
<link rel="stylesheet" href="loopgraph.css">
...
<figure class="lg" data-loopgraph>
  <script type="application/json" src="graphs/agent.json"></script>
  <figcaption>The agent loop, replayed.</figcaption>
</figure>
...
<script src="loopgraph.js"></script>
```

Then `python loopgraph/inline.py doc.html -o out.html` inlines the stylesheet, the script and every graph, checks each graph,
and warns about anything still referenced from outside the file. Ship `out.html`.

## The rules {#rules}

:::checklist Rules for the page
1 one file, self-contained: no CDN, no web fonts it cannot do without, no requests; it works offline
2 both themes, at the token level: colour comes from the page's tokens, never a hex value in a figure
3 wide content scrolls inside its own box; the page itself never scrolls sideways
4 no diagrams drawn with spaces in a code block; every picture is a figure block with a caption
5 data drives the figures: one JSON object per loop figure, exported from code where the code exists
6 generic examples: no real hostnames, people, internal paths or addresses; use example.com and 192.0.2.x
7 no em-dashes or en-dashes anywhere (the renderer refuses them); a comma, a colon or two hyphens instead
8 labels two to four words; the detail goes in doc, which the hover card shows
:::

## Before it ships {#ship}

:::checklist Checks
1 the build runs clean: every graph passes its checks, every cross-reference resolves
2 open the page in a real browser, light then dark; play every loop to the end, through every pause
3 at phone width the rail folds, figures fit or scroll in their box, nothing overflows the page
4 print it, or render the PDF edition, and read one figure on paper
5 read the abstract alone: it should answer the question the document is for
:::
