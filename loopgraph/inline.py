#!/usr/bin/env python3
"""Make a page self-contained: inline the loopgraph component and each figure's graph.

  python inline.py page.html -o out.html

Write the page against files while you work, then run this before you ship:
  <link rel="stylesheet" href="loopgraph.css">          becomes a <style>
  <script src="loopgraph.js"></script>                  becomes an inline <script>
  <script type="application/json" src="g.json"></script>  becomes the graph itself, checked first

Paths resolve against the page's directory, then this script's (so loopgraph.css/js need no copy).
Each graph is checked: edges and run steps name real nodes, consecutive run steps follow an edge.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def find(name, base):
    for d in (base, HERE):
        p = d / name
        if p.exists():
            return p
    sys.exit(f"inline: cannot find {name} beside the page or in {HERE}")


def check(g, name):
    """the same rules the component enforces, caught at build time instead of in a reader's browser"""
    ids = {n["id"] for n in g.get("nodes", [])}
    errs = []
    if len(ids) != len(g.get("nodes", [])):
        errs.append("duplicate node ids")
    groups = {x["id"] for x in g.get("groups", [])}
    for n in g.get("nodes", []):
        if n.get("group") and n["group"] not in groups:
            errs.append(f"node {n['id']} names no group {n['group']}")
    pairs = set()
    for e in g.get("edges", []):
        for end in ("from", "to"):
            if e.get(end) not in ids:
                errs.append(f"edge {e.get('from')} -> {e.get('to')}: no node {e.get(end)}")
        if e.get("kind") == "cond" and not e.get("when"):
            errs.append(f"cond edge {e['from']} -> {e['to']} has no when")
        pairs.add((e.get("from"), e.get("to")))
    prev = None
    for i, s in enumerate(g.get("run", [])):
        if s.get("node") not in ids:
            errs.append(f"run step {i}: no node {s.get('node')}")
        frm = s.get("via") or prev
        if frm and (frm, s.get("node")) not in pairs:
            errs.append(f"run step {i}: no edge {frm} -> {s.get('node')}")
        for k in (s.get("writes") or {}):
            if k not in g.get("state", {}):
                errs.append(f"run step {i}: writes undeclared key {k}")
        prev = s.get("node")
    if errs:
        sys.exit(f"inline: {name}:\n  " + "\n  ".join(errs))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    src = Path(a.page)
    base = src.resolve().parent
    page = src.read_text()

    def css(m):
        return "<style>\n" + find(m.group(1), base).read_text() + "</style>"

    def js(m):
        return "<script>\n" + find(m.group(1), base).read_text() + "</script>"

    def data(m):
        p = find(m.group(1), base)
        g = json.loads(p.read_text())
        check(g, p.name)
        # </ cannot end the script early once escaped
        body = json.dumps(g, ensure_ascii=False, indent=1).replace("</", "<\\/")
        return '<script type="application/json">\n' + body + "\n</script>"

    page = re.sub(r'<link rel="stylesheet" href="([\w./-]+\.css)">', css, page)
    page = re.sub(r'<script type="application/json" src="([\w./-]+\.json)"></script>', data, page)
    page = re.sub(r'<script src="([\w./-]+\.js)"></script>', js, page)
    left = re.findall(r'(?:src|href)="(?!#|https?:|data:)([^"]+)"', page)
    if left:
        print("inline: still references " + ", ".join(sorted(set(left))), file=sys.stderr)
    Path(a.out).write_text(page)
    print(a.out)


if __name__ == "__main__":
    main()
