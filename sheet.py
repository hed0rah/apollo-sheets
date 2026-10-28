"""APOLLO style review sheets: an agent's report in, a printable handbook section out, after the Apollo Operations
Handbook.
Numbered paragraphs in the left gutter, "Figure 2.1-1." captions, drawing numbers, ruled tables, CAUTION blocks,
checklist panels, change bars and a black edge tab. US Letter, black ink, made to be printed and read with a pen.

Any plain Markdown report renders as it is: headings, paragraphs, lists, pipe tables, images. Front matter and
the ::: blocks below add the handbook furniture.

  ---
  title: ATTITUDE CONTROL              (the section's name, set in capitals)
  section: 2.1                         (paragraph and figure numbers hang off this)
  tab: ACS                             (edge tab; drawing numbers run ACS-501A, ACS-502A ...)
  handbook: OPERATIONS HANDBOOK
  system: GUIDANCE AND CONTROL         (second header line)
  doc: ACS-2.1                         (top left)
  mission: EXAMPLE-1                   (footer fields)
  date: 10.26.2026                     (MM.DD.YYYY; ISO is accepted and printed that way)
  change: 10.26.2026                   (optional)
  by: review sheet, from the team notes (optional, under the title)
  paper: cream                         (optional: cream page for screen; default white, for printing)
  ---

  ## Functional description            2.1.1  FUNCTIONAL DESCRIPTION.
  ### Clock synchronization            2.1.1.1  Clock synchronization. (underlined)
  ![Caption](fig.png){width=half}      Figure 2.1-1. Caption, with the next drawing number (width=third too;
                                       gray=1 prints a colour screen capture in black ink)
  :::table Caption                     wraps a pipe table: Table 2.1-1. Caption, above it
  :::caution / :::warning / :::note    the three call-outs
  :::checklist TITLE | ROLE            a boxed procedure in typewriter
  :::changed                           change bar in the gutter beside whatever is inside
  :::diagram Caption                   block diagram or graph: boxes, diamonds, curved back-edges, loops
  :::timeline Caption                  bars on one time axis (handbook.timeline)
  :::plot Caption                      CSV series and exact fn curves, thresholds, limits (handbook.plot)
  :::budget Caption                    used-of-capacity gauges (handbook.budget)
  :::sequence Caption                  messages between actors (handbook.sequence)
  :::signals Caption                   timing diagram: clocks, lines, buses (handbook.signals)
  :::stack Caption                     layers, a memory map (handbook.stack)
  :::bits Caption                      register or packet fields (handbook.bits)
  :::bars Caption                      categorical bars, grouped or stacked (handbook.bars)
  :::matrix Caption                    a comparison of dots (handbook.matrix)
  :::tree Caption                      a hierarchy from an indented outline (handbook.tree)
  :::callouts Caption                  leaders from points on a picture to its margins (handbook.callouts)
  :::scatter Caption                   points, bubbles, a fit line (handbook.scatter)
  :::dist Caption                      box, violin or histogram (handbook.dist)
  :::sankey Caption                    flows between stages (handbook.sankey)
  :::treemap Caption                   nested shares (handbook.treemap)
  :::quadrant Caption                  a named 2 by 2 (handbook.quadrant)
  :::venn Caption                      overlapping sets (handbook.venn)
  :::funnel Caption                    narrowing stages (handbook.funnel)
  $x$  and  $$ ... $$                  inline math; a display, numbered (2.1-1) at the right
  :::equations                         one equation a line, aligned on its relation; a line that starts with
                                       a relation continues the one above, unnumbered
  :::symbols                           the "where" list: SYMBOL | MEANING | UNIT a line, symbol in TeX
  <!-- ... -->                         a comment, never printed
  # Heading                            a part heading, on a new page
  ::::row                              side by side; columns split on a line "|||", closed by "::::"
  :::                                  closes a block

  template.md is a sheet to copy; examples/apollo/apollo.md shows every block beside its source.

  python sheet.py report.md                      writes report.pdf beside it
  python sheet.py report.md -o out.pdf --png     and page PNGs, for a look without a printer
  python sheet.py notes.md -s section=3 -s tab=PHY -s mission=EXAMPLE-1  someone else's report, as it is

A block closes at the first line that is exactly its own colons, so a block that holds other blocks takes four:
::::changed ... ::::, like ::::row. Needs Python 3.8 or later, google-chrome (SHEET_CHROME), matplotlib, numpy,
PyYAML, and the URW base35 fonts (SHEET_FONTS; Debian and Ubuntu: fonts-urw-base35); --png needs pdftoppm.
"""
import argparse
import datetime
import html
import io
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import yaml
from matplotlib import mathtext
from matplotlib.font_manager import FontProperties

import handbook

HERE = Path(__file__).resolve().parent
FONTS = os.environ.get("SHEET_FONTS", "/usr/share/fonts/opentype/urw-base35")
CHROME = os.environ.get("SHEET_CHROME", "google-chrome")


# -- math and inline ---------------------------------------------------------------------------------------------------

_MATH = {}
RELATION = re.compile(r"=|<|>|\\(approx|equiv|simeq|sim|cong|propto|neq?|leq?|geq?|ll|gg|in|ni|subseteq?|"
                      r"to|mapsto|rightarrow|Rightarrow|iff)(?![a-zA-Z])")


def math(tex, display=False):
    """TeX as an inline SVG through matplotlib's mathtext (STIX, to sit with the Roman body); what mathtext cannot
    parse comes back as the TeX itself in typewriter, so nothing is lost"""
    key = (tex, display)
    if key not in _MATH:
        clean = re.sub(r"\\boxed\{(.*)\}", r"\1", tex.strip())
        # mathtext has no \text and wants braces on \sqrt
        clean = re.sub(r"\\text\{([^}]*)\}", lambda m: r"\mathrm{" + m.group(1).replace(" ", r"\ ") + "}", clean)
        clean = re.sub(r"\\sqrt\s+(\w)", r"\\sqrt{\1}", clean)
        buf = io.StringIO()
        try:
            with plt.rc_context({"mathtext.fontset": "stix", "svg.fonttype": "path"}):
                depth = mathtext.math_to_image(f"${clean}$", buf, prop=FontProperties(size=11 if display else 9.6),
                                               dpi=72, format="svg")
            svg = buf.getvalue()
            svg = svg[svg.index("<svg"):].strip()
            svg = svg.replace("<svg ", f'<svg class="math" style="vertical-align:{-depth:.2f}pt" ', 1)
            cls = "boxed" if "\\boxed" in tex else ""
            _MATH[key] = f'<span class="{cls}">{svg}</span>'
        except Exception:
            _MATH[key] = f"<code>{html.escape(tex)}</code>"
    return _MATH[key]


def inline(s, upper=False):
    """Markdown marks and $math$ to HTML; upper sets the words in capitals but leaves math and code alone"""
    held = []

    def hold(frag):
        held.append(frag)
        return f"\x00{len(held) - 1}\x00"

    # code first, so a $ inside backticks stays a dollar sign
    s = re.sub(r"`([^`]+)`", lambda m: hold(f"<code>{html.escape(m.group(1), quote=False)}</code>"), s)
    s = re.sub(r"(?<![\\$\w])\$(?=\S)([^$\n]+?)(?<=\S)\$(?![\w$])", lambda m: hold(math(m.group(1))), s)
    if upper:
        s = s.upper()
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*([^*]+)\*(?![\w*])", r"<i>\1</i>", s)
    s = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"<u>\1</u>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", s)               # paper has no links: keep the words
    s = re.sub(r"\^([^^\s]+)\^", r"<sup>\1</sup>", s)
    s = re.sub(r"~([^~\s]+)~", r"<sub>\1</sub>", s)
    s = s.replace(" -- ", " &ndash; ")
    # a number keeps its % or unit, and 69 540 its groups, on one line
    s = re.sub(r"(?<=\d) (?=\d{3}\b|%|[kMG]?(B|Hz|s|ms|us|V|mV|A|mA|W|dB|m|mm|in|pt)\b)", "&nbsp;", s)
    return re.sub(r"\x00(\d+)\x00", lambda m: held[int(m.group(1))], s)


# -- the document ------------------------------------------------------------------------------------------------------

class Sheet:
    def __init__(self, meta, base):
        self.m = meta
        self.base = base
        self.sec = str(meta.get("section", "1"))
        self.count = [0, 0, 0]                  # ##, ###, ####
        self.fig = self.tab = self.eq = 0
        self.dwg = 500

    def number(self, level):
        self.count[level] += 1
        for i in range(level + 1, len(self.count)):
            self.count[i] = 0
        return ".".join([self.sec] + [str(c) for c in self.count[: level + 1]])

    def drawing(self):
        self.dwg += 1
        return f"{self.m.get('tab', 'DWG')}-{self.dwg}A"

    def figure(self, body, caption, width=""):
        self.fig += 1
        cap = f"Figure {self.sec}-{self.fig}.&ensp;{inline(caption)}" if caption else f"Figure {self.sec}-{self.fig}."
        return (f'<figure class="{width}"><div class="art">{body}<span class="dwg">{self.drawing()}</span></div>'
                f"<figcaption>{cap}</figcaption></figure>")

    def eqno(self):
        self.eq += 1
        return f'<span class="eqno">({self.sec}-{self.eq})</span>'

    def equations(self, body):
        """one equation per line, aligned on its first top-level relation (or on & where the line has one)"""
        rows = []
        for line in (l.strip() for l in body if l.strip()):
            if "&" in line:
                lhs, rhs = line.split("&", 1)
            else:
                cut = next((m.start() for m in RELATION.finditer(line)
                            if line[:m.start()].count("{") == line[:m.start()].count("}")), None)
                lhs, rhs = (line[:cut], line[cut:]) if cut is not None else ("", line)
            continued = not lhs.strip() and RELATION.match(rhs.strip()) is not None   # starts with a relation
            rows.append(f'<span class="lhs">{math(lhs, True) if lhs.strip() else ""}</span>'
                        f'<span class="rhs">{math(rhs, True)}</span>'
                        + ("<span></span>" if continued else self.eqno()))     # a continuation takes no number
        return '<div class="equations">' + "".join(rows) + "</div>"

    def symbols(self, body):
        """SYMBOL | MEANING | UNIT, one per line, set as the handbook's "where" list"""
        rows = []
        for line in (l for l in body if l.strip()):
            sym, mean, unit = ([c.strip() for c in _cells(line)] + ["", ""])[:3]
            rows.append(f"<tr><td>{math(sym)}</td><td>=</td><td>{inline(mean)}</td>"
                        f"<td>{inline(unit)}</td></tr>")
        return f'<div class="where"><span>where</span><table>{"".join(rows)}</table></div>'

    # blocks: returns html for a list of lines
    def blocks(self, lines):
        out, i = [], 0
        para = []

        def flush():
            if para:
                out.append(f"<p>{inline(' '.join(para))}</p>")
                para.clear()

        while i < len(lines):
            line = lines[i]
            s = line.strip()
            fence = re.match(r"^(:{3,})\s*(\w+)?\s*(.*)$", s)
            if fence and fence.group(2):
                flush()
                colons, kind, arg = fence.groups()
                j = i + 1
                while j < len(lines) and lines[j].strip() != colons:
                    j += 1
                if j == len(lines):
                    raise SystemExit(f"sheet: {colons}{kind} {arg} opens but never closes with a line {colons} "
                                     "(a block that holds blocks takes four colons, ::::changed ... ::::)")
                out.append(self.directive(kind, arg.strip(), lines[i + 1: j]))
                i = j + 1
                continue
            if s.startswith("$$"):
                flush()
                j, tex = i, s[2:]
                while "$$" not in tex and j + 1 < len(lines):
                    j += 1
                    tex += " " + lines[j].strip()
                out.append(f'<div class="display">{math(tex.split("$$")[0], display=True)}{self.eqno()}</div>')
                i = j + 1
                continue
            if s.startswith("<!--"):                       # guidance in a template, never printed
                flush()
                while i < len(lines) and "-->" not in lines[i]:
                    i += 1
                if i < len(lines) and lines[i].split("-->", 1)[1].strip():
                    lines[i] = lines[i].split("-->", 1)[1]     # what follows the comment on its line still prints
                    continue
                i += 1
                continue
            if s.startswith("```"):
                flush()
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith("```"):
                    j += 1
                out.append(f"<pre>{html.escape(chr(10).join(lines[i + 1: j]))}</pre>")
                i = j + 1
                continue
            if not s:
                flush()
            elif re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", s):
                flush()
                out.append("<hr>")
            elif m := re.match(r"^(#{1,4})\s+(.*)$", s):
                flush()
                out.append(self.heading(len(m.group(1)), m.group(2)))
            elif m := re.match(r"^!\[([^\]]*)\]\(([^)]+)\)(\{[^}]*\})?$", s):
                flush()
                opts = dict(re.findall(r"(\w+)=(\S+?)(?=[\s}])", m.group(3) or ""))
                out.append(self.image(m.group(2), m.group(1), (opts.get("width", "") + (" gray" if "gray" in opts else "")).strip()))
            elif s.startswith("|"):
                flush()
                j = i
                while j < len(lines) and lines[j].strip().startswith("|"):
                    j += 1
                out.append(self.table(lines[i:j]))
                i = j
                continue
            elif re.match(r"^([-*]|\d+[.)])\s+", s):
                flush()
                j = i
                items = []
                while j < len(lines) and lines[j].strip():
                    t = lines[j].strip()
                    if re.match(r"^([-*]|\d+[.)])\s+", t):
                        items.append(re.sub(r"^([-*]|\d+[.)])\s+", "", t))
                    else:
                        items[-1] += " " + t
                    j += 1
                tag = "ol" if re.match(r"^\d", s) else "ul"
                out.append(f"<{tag}>" + "".join(f"<li>{inline(t)}</li>" for t in items) + f"</{tag}>")
                i = j
                continue
            else:
                para.append(s)
            i += 1
        flush()
        return "\n".join(out)

    def heading(self, level, text):
        text = re.sub(r"^(\d+\.)+\d*\s+|^\d+(\.\d+)+\s+", "", text)      # 2.1, 2.1., 3. but not a year
        if level == 1 and not self.m.get("title"):
            self.m["title"] = text
            return ""
        if level == 1:
            return f'<h1>{inline(text, upper=True)}</h1>'
        num = self.number(level - 2)
        if level == 2:
            return f'<h2><span class="num">{num}</span>{inline(text.rstrip("."), upper=True)}.</h2>'
        return f'<h{level}><span class="num">{num}</span><u>{inline(text.rstrip("."))}.</u></h{level}>'

    def image(self, src, caption, width):
        path = (self.base / src).resolve()
        if not path.exists():
            raise SystemExit(f"sheet: image not found: {src}")
        if path.suffix == ".svg":
            body = path.read_text()
            body = body[body.index("<svg"):]
        else:
            body = f'<img src="{path.as_uri()}">'
        return self.figure(body, caption, width)

    def table(self, rows, caption=None):
        cells = [[c.strip() for c in _cells(r)] for r in rows]
        head, body = cells[0], [r for r in cells[1:] if not all(re.fullmatch(r":?-+:?", c) for c in r)]
        title = ""
        if caption is not None:
            self.tab += 1
            title = f'<div class="ttitle">Table {self.sec}-{self.tab}.&ensp;{inline(caption)}</div>'
        th = "".join(f"<th>{inline(c)}</th>" for c in head)
        tr = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
        return f'<div class="table">{title}<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'

    def directive(self, kind, arg, body):
        try:
            return self._directive(kind, arg, body)
        except (KeyError, ValueError, IndexError, ArithmeticError, TypeError, FileNotFoundError,
                StopIteration) as e:
            # a figure's spec is wrong: say which block and what, not a traceback
            raise SystemExit(f"sheet: :::{kind} {arg}: {type(e).__name__}: {e}")

    def _directive(self, kind, arg, body):
        text = "\n".join(body)
        if not text.strip() and kind not in ("changed", "row"):
            raise SystemExit(f"sheet: :::{kind} {arg} is empty")
        if kind == "table":
            rows = [l for l in body if l.strip().startswith("|")]
            return self.table(rows, arg)
        if kind in ("caution", "warning", "note"):
            return f'<div class="{kind}"><div class="ctitle">{kind.upper()}</div>{self.blocks(body)}</div>'
        if kind == "checklist":
            title, _, role = (p.strip() for p in arg.partition("|"))
            lines = "".join(f"<div>{inline(l.rstrip())}</div>" for l in body if l.strip())
            return (f'<div class="checklist"><div class="chead"><span>{inline(title, upper=True)}</span>'
                    f'<span class="role">{inline(role, upper=True)}</span></div><div class="cbody">{lines}</div></div>')
        if kind == "changed":
            return f'<div class="changed">{self.blocks(body)}</div>'
        if kind == "row":
            cols, cur = [], []
            for l in body:
                if l.strip() == "|||":
                    cols.append(cur)
                    cur = []
                else:
                    cur.append(l)
            cols.append(cur)
            return '<div class="row">' + "".join(f"<div>{self.blocks(c)}</div>" for c in cols) + "</div>"
        if kind == "equations":
            return self.equations(body)
        if kind == "symbols":
            return self.symbols(body)
        if kind in ("diagram", "timeline", "sequence", "signals", "budget"):
            return self.figure(getattr(handbook, kind)(text), arg, "wide")
        if kind in ("stack", "bits", "bars", "matrix", "tree", "sankey", "treemap", "quadrant", "venn", "funnel"):
            return self.figure(getattr(handbook, kind)(text), arg)          # drawn to print size
        if kind in ("callouts", "scatter", "dist"):
            return self.figure(getattr(handbook, kind)(text, self.base), arg)
        if kind == "plot":
            wide = re.search(r"^\s*size\s+wide\b", text, re.M)
            return self.figure(handbook.plot(text, self.base), arg, "wide" if wide else "")
        raise SystemExit(f"sheet: unknown block :::{kind}")


def _cells(row):
    """a pipe-table row's cells: a | inside $math$ or `code`, or written \\|, stays in its cell"""
    row = row.strip()
    row = row[1:] if row.startswith("|") else row
    row = row[:-1] if row.endswith("|") and not row.endswith("\\|") else row
    out, cur, quote = [], "", None
    i = 0
    while i < len(row):
        ch = row[i]
        if ch == "\\" and row[i + 1: i + 2] == "|":
            cur += "|"
            i += 2
            continue
        if ch in "$`":
            quote = None if quote == ch else (quote or ch)
        if ch == "|" and not quote:
            out.append(cur)
            cur = ""
        else:
            cur += ch
        i += 1
    return out + [cur]


def split_front(src):
    if src.startswith("---\n"):
        end = src.find("\n---", 4)
        if end < 0:
            raise SystemExit("sheet: front matter opens with --- but never closes")
        return yaml.safe_load(src[4:end]) or {}, src[end + 4:].lstrip("\n")
    return {}, src


def mdy(v):
    """reader-facing dates print MM.DD.YYYY; front matter may give that or ISO (which yaml reads as a date)"""
    if isinstance(v, datetime.date):
        return v.strftime("%m.%d.%Y")
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", str(v).strip())
    return f"{m[2]}.{m[3]}.{m[1]}" if m else str(v)


def css(m):
    q = lambda s: '"' + str(s).replace('"', "'") + '"'
    paper = "#F3EBD3" if m.get("paper") == "cream" else "#FFFFFF"
    footer = f"Mission {m.get('mission', '')}  Basic Date {mdy(m.get('date', ''))}" \
             f"  Change Date {mdy(m.get('change', ''))}"
    return (HERE / "sheet.css").read_text().replace("{FONTS}", FONTS).replace("{PAPER}", paper) \
        .replace("{DOC}", q(m.get("doc", ""))) \
        .replace("{HANDBOOK}", q(str(m.get("handbook", "OPERATIONS HANDBOOK")).upper())) \
        .replace("{SYSTEM}", q(str(m.get("system", m.get("title", ""))).upper())) \
        .replace("{FOOTER}", q(footer)).replace("{SEC}", q(m.get("section", "1")))


def render(src_path, overrides=()):
    src_path = Path(src_path).resolve()
    meta, body = split_front(src_path.read_text())
    meta.update(o.split("=", 1) for o in overrides)
    sheet = Sheet(meta, src_path.parent)
    content = sheet.blocks(body.splitlines())          # first, so a report's own "# title" can fill the header
    tab = html.escape(str(meta.get("tab", "")))
    head = f'<div class="title">{inline(str(meta.get("title", "")).upper())}</div>'
    if meta.get("by"):
        head += f'<div class="by">{inline(str(meta["by"]))}</div>'
    title = html.escape(str(meta.get("doc") or meta.get("title", "")))       # the PDF's title, not sheet.html
    return (f'<!doctype html><html><head><meta charset="utf-8"><title>{title}</title><style>{css(sheet.m)}</style></head><body>'
            f'<div class="edgetab">{tab}</div>{head}<main>{content}</main></body></html>')


def main():
    ap = argparse.ArgumentParser(description="render a report as a handbook-style review sheet (PDF)")
    ap.add_argument("src")
    ap.add_argument("-o", "--out")
    ap.add_argument("-s", "--set", action="append", default=[], metavar="KEY=VALUE",
                    help="front-matter field, over the file's own: ingest a report without editing it")
    ap.add_argument("--png", action="store_true", help="also write page PNGs at 110 dpi beside the PDF")
    ap.add_argument("--html", action="store_true", help="keep the intermediate HTML beside the PDF")
    a = ap.parse_args()
    out = Path(a.out or Path(a.src).with_suffix(".pdf")).resolve()
    page = render(a.src, a.set)
    out.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp) / "sheet.html"
        h.write_text(page)
        r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                            "--allow-file-access-from-files", f"--print-to-pdf={out}", h.as_uri()],
                           capture_output=True, text=True)
        if not out.exists():
            sys.exit(f"sheet: chrome wrote no pdf\n{r.stderr[-2000:]}")
    if a.html:
        out.with_suffix(".html").write_text(page)
    if a.png:
        subprocess.run(["pdftoppm", "-png", "-r", "110", str(out), str(out.with_suffix(""))], check=True)
    print(out)


if __name__ == "__main__":
    main()
