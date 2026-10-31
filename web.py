"""The same Markdown, as an Interactive Whitepaper: one self-contained HTML page for a screen, beside the printed sheet.

  python web.py report.md                  writes report.html beside it
  python web.py report.md -o out.html      or there
  python web.py notes.md -s status=Final   front-matter fields over the file's own, as for sheet.py

The source is a sheet.py source, unchanged: front matter and the ::: blocks. sheet.py's block renderers draw every
figure; this file only dresses the result in the Interactive Whitepaper (house-styles spec/template.html, its head and
styles kept verbatim): a cover from the front matter, ## headings as numbered chapters, a rail with the contents,
scroll-spy and the cross-references, light and dark.

Figures come out as inline SVG with their lettering drawn as paths, so the page needs no font file, and their ink
and greys are rewritten to the page's colour tokens, so a figure turns with the theme. A figure holding a raster (a
picture, a spectrogram) cannot turn, so in the dark it sits on a light plate. Links work here: [text](#anchor) to a
heading's slug, or to fig-N.M / tab-N.M, and every such link is listed in the rail. Front matter beyond sheet.py's:
status (the pill, Draft by default), abstract (a paragraph above the first chapter), eyebrow (over the title).
A heading may carry its own anchor, ## The gate {#gate}; sheet.py leaves it off the paper.

The page shell is the Interactive Whitepaper template, web-template.html beside this file, or SHEET_TEMPLATE.
"""
import argparse
import base64
import html
import os
import re
from pathlib import Path

import handbook
import sheet

TEMPLATE = Path(os.environ.get("SHEET_TEMPLATE", Path(__file__).resolve().parent / "web-template.html"))
handbook.STYLE["svg.fonttype"] = "path"          # lettering as outlines: exact, and nothing for the page to fetch

# the template is light only; dark tokens as in the NERV pages, plus what this renderer adds
EXTRA = """<style>
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --canvas:#111417;--paper:#191D21;--ink:#E2E5E8;--ink-2:#B3BBC3;--ink-3:#87919B;
    --rule:#2A3036;--rule-2:#3B444C;--slate:#93B2CD;--slate-2:#7893AB;--slate-soft:#22303B;
    --teal:#63B5A8;--orange:#E0905F;--ok:#80BB89;--warn:#D4A85C;--crit:#E27F75;
    --code-bg:#14181B;--code-ink:#D3D9DE;
    --kw:#93B2CD;--str:#80BB89;--num:#D4A85C;--cm:#8A929A;--fn:#E0905F;
    color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --canvas:#111417;--paper:#191D21;--ink:#E2E5E8;--ink-2:#B3BBC3;--ink-3:#87919B;
  --rule:#2A3036;--rule-2:#3B444C;--slate:#93B2CD;--slate-2:#7893AB;--slate-soft:#22303B;
  --teal:#63B5A8;--orange:#E0905F;--ok:#80BB89;--warn:#D4A85C;--crit:#E27F75;
  --code-bg:#14181B;--code-ink:#D3D9DE;
  --kw:#93B2CD;--str:#80BB89;--num:#D4A85C;--cm:#8A929A;--fn:#E0905F;
  color-scheme:dark;
}
:root[data-theme="light"]{color-scheme:light}
/* counters scoped to the chapter section (Chrome keeps a counter-reset on the h2 from reaching what follows) */
.chapter{counter-reset:sec fig tab}
.chapter>h2{counter-reset:none}
.theme-btn{font-family:var(--sans);font-size:.72rem;background:none;border:1px solid var(--rule-2);
  color:var(--ink-2);border-radius:2px;padding:.2rem .55rem;cursor:pointer}
.theme-btn:hover{color:var(--ink);border-color:var(--slate)}
.cover .by{font-family:var(--sans);font-size:.78rem;color:var(--ink-3);margin:.9rem 0 0}
figure.fig{margin:1.6rem 0;text-align:center}
figure.fig .art{display:inline-block;max-width:100%}
figure.fig svg{max-width:100%;height:auto;display:block;margin:0 auto}
figure.fig img{max-width:100%;height:auto}
figure.fig figcaption{text-align:left}
figure.plate .art{background:#FDFDFC;padding:.6rem;border-radius:2px}
.paper svg.math{fill:var(--ink);overflow:visible}
.display{position:relative;text-align:center;margin:1rem 0}
.display .eqno,.equations .eqno{font-family:var(--sans);font-size:.8rem;color:var(--ink-2)}
.display .eqno{position:absolute;right:0;top:50%;transform:translateY(-50%)}
.equations{display:grid;grid-template-columns:1fr auto auto;column-gap:.3rem;row-gap:.5rem;align-items:center;margin:1rem 0}
.equations .lhs{text-align:right}
.equations .eqno{justify-self:end;padding-left:2rem}
.where{display:flex;gap:.8rem;margin:0 0 1rem 2rem;font-size:.95rem}
.where>span{font-style:italic;color:var(--ink-2)}
.where table{margin:0;border:none;width:auto}
.where td{border:none;padding:0 .5rem .1rem 0}
.where td:first-child{text-align:right}
.where td:last-child{font-style:italic;color:var(--ink-2)}
.boxed svg{border:1px solid var(--ink);padding:3px 6px}
svg.spark{vertical-align:-1px}
.procedure{margin:1.4rem 0}
.procedure .lbl{font-family:var(--sans);font-size:.66rem;font-weight:700;letter-spacing:.1em;
  text-transform:uppercase;color:var(--slate);margin:0 0 .3rem}
.procedure .lbl .role{color:var(--ink-3);font-weight:600;margin-left:.6rem}
.procedure .n{display:inline-block;min-width:1.6em;font-family:var(--mono);font-size:.8rem;color:var(--ink-3)}
.changed{border-left:3px solid var(--orange);padding-left:1rem;margin-left:-1.2rem}
.cols>.col>:first-child{margin-top:0}
.paper a:not(.ref){color:var(--slate)}
</style>
"""

THEME_JS = """<script>
(function(){
  var root = document.documentElement;
  try { var th = localStorage.getItem('spec-theme'); if (th) root.setAttribute('data-theme', th); } catch (e) {}
  var tb = document.getElementById('theme-btn');
  if (tb) tb.addEventListener('click', function(){
    var cur = root.getAttribute('data-theme');
    if (!cur) cur = (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
    var nx = cur === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', nx);
    try { localStorage.setItem('spec-theme', nx); } catch (e) {}
  });
})();
</script>
"""


def slug(text):
    """a heading's anchor, as GitHub makes it, so links written for the Markdown work here too"""
    text = re.sub(r"<[^>]+>|`", "", text).lower()
    return re.sub(r"[^\w\- ]", "", text).strip().replace(" ", "-")


def tint(hexcol):
    """a grey to the page's ink-to-paper ramp, so it turns with the theme; a colour stays a colour"""
    h = hexcol.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    if max(r, g, b) - min(r, g, b) > 6:
        return hexcol
    light = (r + g + b) / 765
    if light <= 0.1:
        return "var(--ink)"
    if light >= 0.97:
        return "var(--paper)"
    return f"color-mix(in srgb, var(--ink) {round((1 - light) * 100)}%, var(--paper))"


COLOR = re.compile(r"((?:fill|stroke|stop-color|color)\s*[:=]\s*\"?)(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})\b")


def retint(svg):
    return COLOR.sub(lambda m: m.group(1) + tint(m.group(2)), svg)


def sized(svg, scale=1.55):
    """print size in pt to screen pixels, a little larger, never wider than the column"""
    m = re.search(r'<svg[^>]*?\swidth="([\d.]+)pt"\s+height="([\d.]+)pt"', svg)
    if not m:
        return svg
    w = float(m.group(1)) * 4 / 3 * scale
    svg = svg.replace(m.group(0), m.group(0).replace(f'width="{m.group(1)}pt"', "")
                      .replace(f'height="{m.group(2)}pt"', f'style="width:{w:.0f}px"'), 1)
    return svg


_N = [0]


def private_ids(svg):
    """each figure's ids under its own prefix: matplotlib reuses glyph and clip ids from figure to figure"""
    _N[0] += 1
    p = f"s{_N[0]}-"
    svg = re.sub(r'\bid="([^"]+)"', lambda m: f'id="{p}{m.group(1)}"', svg)
    svg = re.sub(r'url\(#([^)]+)\)', lambda m: f"url(#{p}{m.group(1)})", svg)
    return re.sub(r'(xlink:href|href)="#([^"]+)"', lambda m: f'{m.group(1)}="#{p}{m.group(2)}"', svg)


def clean_svg(svg):
    return re.sub(r"<metadata>.*?</metadata>\s*", "", svg, flags=re.S)


_LINKS = []                                         # (text, href) of every in-document link, in order
_inline = sheet.inline


def inline(s, upper=False):
    """sheet.inline, but a link stays a link (paper has none) and a sparkline turns with the theme"""
    held = []

    def hold(m):
        text, href = m.group(1), m.group(2)
        if href.startswith("#"):
            _LINKS.append((text, href[1:]))
            held.append((f'<a class="ref" href="{html.escape(href)}">', text))
        else:
            held.append((f'<a href="{html.escape(href)}">', text))
        return f"\x02{len(held) - 1}\x02"

    # links out first, their words rendered on their own, so the anchor survives sheet's escaping
    s = re.sub(r"(?<!!)\[([^\]]+)\]\(([^)\s]+)\)", hold, s)
    out = _inline(s, upper)
    out = re.sub(r"\x02(\d+)\x02", lambda m: held[int(m.group(1))][0] + _inline(held[int(m.group(1))][1], upper) + "</a>",
                 out)
    out = out.replace(" &ndash; ", " -- ")              # the house aside, not a dash
    return retint(out) if "spark" in out else out


sheet.inline = inline


class Page(sheet.Sheet):
    def __init__(self, meta, base):
        super().__init__(meta, base)
        self.chap = 0
        self.figs = self.tabs = self.eqs = 0
        self.ids = {}                               # anchor -> label for the rail
        self.items = []                             # (anchor, label, caption) for figures and tables
        self.used = set()
        self.sub = 0

    def anchor(self, text):
        a = slug(text) or "s"
        base, n = a, 1
        while a in self.used:
            a = f"{base}-{n}"
            n += 1
        self.used.add(a)
        return a

    def heading(self, level, text):
        text = re.sub(r"^(\d+\.)+\d*\s+|^\d+(\.\d+)+\s+", "", text)
        if level == 1 and not self.m.get("title"):
            self.m["title"] = text
            return ""
        m = re.search(r"\s*\{#([\w-]+)\}$", text)          # an explicit anchor: ## Heading {#name}
        if m:
            text = text[:m.start()]
        a = m.group(1) if m else self.anchor(text)
        self.used.add(a)
        if level <= 2:
            self.chap += 1
            self.figs = self.tabs = self.eqs = 0
            self.sub = 0
            self.ids[a] = f"&sect;{self.chap}"
            return f"\x01{a}\x03{inline(text.rstrip('.'))}\x01"
        if level == 3:
            self.sub += 1
            self.ids[a] = f"&sect;{self.chap}.{self.sub}"
        return f'<h{level} id="{a}">{inline(text.rstrip("."))}</h{level}>'

    def figure(self, body, caption, width=""):
        self.figs += 1
        a = f"fig-{self.chap}.{self.figs}"
        label = f"Fig. {self.chap}.{self.figs}"
        self.ids[a] = label
        self.items.append((a, label, caption))
        plate = "<image" in body or "<img" in body
        if body.lstrip().startswith("<svg"):
            body = private_ids(clean_svg(body))
            body = sized(body) if plate else retint(sized(body))
        cls = "fig scroll plate" if plate else "fig scroll"
        return (f'<figure class="{cls}" id="{a}"><div class="art">{body}</div>'
                f'<figcaption class="cap">{inline(caption) if caption else ""}</figcaption></figure>')

    def image(self, src, caption, width):
        path = (self.base / src).resolve()
        if not path.exists():
            raise SystemExit(f"web: image not found: {src}")
        if path.suffix == ".svg":
            body = path.read_text()
            return self.figure(body[body.index("<svg"):], caption, width)
        mime = {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".gif": "gif", ".webp": "webp"}.get(path.suffix.lower(), "png")
        uri = f"data:image/{mime};base64," + base64.b64encode(path.read_bytes()).decode()
        return self.figure(f'<img src="{uri}" alt="{html.escape(caption)}">', caption, width)

    def table(self, rows, caption=None):
        cells = [[c.strip() for c in sheet._cells(r)] for r in rows]
        head, body = cells[0], [r for r in cells[1:] if not all(re.fullmatch(r":?-+:?", c) for c in r)]
        idattr, cap = "", ""
        if caption is not None:
            self.tabs += 1
            a = f"tab-{self.chap}.{self.tabs}"
            label = f"Table {self.chap}.{self.tabs}"
            self.ids[a] = label
            self.items.append((a, label, caption))
            idattr, cap = f' id="{a}"', f"<caption>{inline(caption)}</caption>"
        th = "".join(f"<th>{inline(c)}</th>" for c in head)
        tr = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
        return f'<div class="scroll"{idattr}><table>{cap}<thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'

    def eqno(self):
        self.eqs += 1
        return f'<span class="eqno">({self.chap}.{self.eqs})</span>'

    def blocks(self, lines):
        # code blocks become the template's code panel; everything else is sheet's
        out = super().blocks(lines)
        return re.sub(r"<pre>(.*?)</pre>", r'<div class="scroll"><pre class="code">\1</pre></div>', out, flags=re.S)

    def _directive(self, kind, arg, body):
        if kind in ("caution", "warning", "note"):
            cls = {"note": "note", "caution": "note warn", "warning": "note crit"}[kind]
            return f'<div class="{cls}"><span class="lbl">{kind.capitalize()}</span>{self.blocks(body)}</div>'
        if kind == "checklist":
            title, _, role = (p.strip() for p in arg.partition("|"))
            items = []
            for l in (l.strip() for l in body if l.strip()):
                m = re.match(r"(\d+)\s+(.*)", l)
                n, t = (m.group(1), m.group(2)) if m else ("", l)
                num = f'<span class="n">{n}</span>' if n else ""
                items.append(f'<li><span class="box" aria-hidden="true"></span><span class="txt">{num}{inline(t)}</span></li>')
            r = f'<span class="role">{inline(role)}</span>' if role else ""
            return (f'<div class="procedure"><p class="lbl">{inline(title)}{r}</p>'
                    f'<ul class="check">{"".join(items)}</ul></div>')
        if kind == "row":
            cols, cur = [], []
            for l in body:
                if l.strip() == "|||":
                    cols.append(cur)
                    cur = []
                else:
                    cur.append(l)
            cols.append(cur)
            return '<div class="cols">' + "".join(f'<div class="col">{self.blocks(c)}</div>' for c in cols) + "</div>"
        return super()._directive(kind, arg, body)


def chapters(content, meta):
    """split at the chapter markers into <section>s; anything before the first is the abstract"""
    parts = re.split(r"\x01([^\x03]+)\x03([^\x01]*)\x01", content)
    head, rest = parts[0], parts[1:]
    out, toc = [], []
    lead = (f"<p>{inline(str(meta['abstract']))}</p>" if meta.get("abstract") else "") + head.strip()
    if lead.strip():
        out.append(f'<section id="abstract" class="abstract" aria-labelledby="abstract-h">'
                   f'<span class="lbl" id="abstract-h">Abstract</span>{lead}</section>')
        toc.append(("abstract", "Abstract", "0"))
    for i in range(0, len(rest), 3):
        a, title, body = rest[i], rest[i + 1], rest[i + 2]
        out.append(f'<section class="chapter" id="{a}" aria-labelledby="{a}-h">'
                   f'<h2 id="{a}-h">{title}</h2>{body}</section>')
        toc.append((a, re.sub(r"<[^>]+>", "", title), str(i // 3 + 1)))
    return "\n".join(out), toc


def rail(page, toc, meta, status):
    li = "\n".join(f'        <li><a href="#{a}"><span class="n">{n}</span>{t}</a></li>' for a, t, n in toc)
    seen, xref = set(), []
    for text, a in _LINKS:
        label = page.ids.get(a, "")
        if not label:
            raise SystemExit(f"web: link to #{a} ({text}) has no target in the document")
        if a in seen:                               # one line a target, under the words first used for it
            continue
        seen.add(a)
        words = inline(text)
        tail = "" if html.unescape(label) in html.unescape(re.sub(r"<[^>]+>", "", words)) else f" {label}"
        xref.append(f'          <li><a href="#{a}">{words}{tail}</a></li>')
    figs = [f'          <li><a href="#{a}">{label} {inline(cap)}</a></li>' for a, label, cap in page.items if cap]
    groups = ""
    if xref:
        groups += ('      <div class="grp internal" aria-label="Cross-references">\n        <p class="glbl">Cross-references</p>\n'
                   f'        <ul>\n{chr(10).join(xref)}\n        </ul>\n      </div>\n')
    if figs:
        groups += ('      <div class="grp internal" aria-label="Figures and tables">\n        <p class="glbl">Figures and tables</p>\n'
                   f'        <ul>\n{chr(10).join(figs)}\n        </ul>\n      </div>\n')
    doc = html.escape(str(meta.get("doc", "")))
    when = sheet.mdy(meta.get("date", ""))
    return f"""  <aside class="rail" aria-label="Table of contents">
    <p class="doc-id">{doc}{" &middot; " + when if when else ""}</p>
    <nav aria-label="Sections">
      <ol id="toc">
{li}
      </ol>
    </nav>
    <div class="rail-refs">
{groups}    </div>
    <div class="rail-foot">
      <div class="stat-row"><span class="k">Status</span><span class="pill slate">{html.escape(status)}</span></div>
      <button class="theme-btn" id="theme-btn" type="button">Light / dark</button>
    </div>
  </aside>"""


def cover(meta, status):
    rows = [("Document", meta.get("doc")), ("Section", meta.get("section")), ("Mission", meta.get("mission")),
            ("Date", sheet.mdy(meta["date"]) if meta.get("date") else None),
            ("Changed", sheet.mdy(meta["change"]) if meta.get("change") else None)]
    dl = "".join(f"<div><dt>{k}</dt><dd>{html.escape(str(v))}</dd></div>" for k, v in rows if v)
    dl += f'<div><dt>Status</dt><dd><span class="pill slate">{html.escape(status)}</span></dd></div>'
    eyebrow = meta.get("eyebrow") or meta.get("handbook") or ""
    sub = f'<p class="sub">{inline(str(meta["system"]))}</p>' if meta.get("system") else ""
    by = f'<p class="by">{inline(str(meta["by"]))}</p>' if meta.get("by") else ""
    return (f'    <header class="cover">\n      <p class="eyebrow">{inline(str(eyebrow))}</p>\n'
            f'      <h1>{inline(str(meta.get("title", "")))}</h1>\n      {sub}\n      <dl class="meta">{dl}</dl>\n      {by}\n'
            f"    </header>")


MATHSVG = re.compile(r'<svg class="math" style="vertical-align:(-?[\d.]+)pt"(.*?)width="([\d.]+)pt" height="([\d.]+)pt"')
MATHSCALE = 1.4                                     # sheet sets math at 9.6 and 11 pt to sit in 9.6 pt Roman; this body is 17 px


def split_template():
    if not TEMPLATE.exists():
        raise SystemExit(f"web: no page template at {TEMPLATE}; set SHEET_TEMPLATE to the Interactive Whitepaper template")
    t = TEMPLATE.read_text()
    head = t[: t.index("</head>")]
    script = t[t.index("<script>"): t.index("</script>") + len("</script>")]
    spy = script[: script.index("// ---- event-trace scrubber")] + "})();\n</script>"    # the scrubber needs page data
    return head, spy


def render(src_path, overrides=()):
    src_path = Path(src_path).resolve()
    meta, body = sheet.split_front(src_path.read_text())
    meta.update(o.split("=", 1) for o in overrides)
    _LINKS.clear()
    page = Page(meta, src_path.parent)
    content, toc = chapters(page.blocks(body.splitlines()), meta)
    content = MATHSVG.sub(lambda m: f'<svg class="math" style="vertical-align:{float(m[1]) * MATHSCALE:.2f}pt"{m[2]}'
                          f'width="{float(m[3]) * MATHSCALE:.1f}pt" height="{float(m[4]) * MATHSCALE:.1f}pt"', content)
    status = str(meta.get("status", "Draft"))
    head, spy = split_template()
    title = html.escape(f'{meta.get("title", "")}{" -- " + str(meta["doc"]) if meta.get("doc") else ""}')
    head = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", head, flags=re.S)
    when = sheet.mdy(meta.get("date", ""))
    foot = " &middot; ".join(html.escape(str(x)) for x in (meta.get("doc"), when, status) if x)
    page_html = f"""{head}{EXTRA}</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="doc">
{rail(page, toc, meta, status)}
  <main class="paper" id="main">
{cover(meta, status)}
{content}
    <footer>
      <span>{foot}</span>
      <span>{inline(str(meta.get("mission", "")))}</span>
    </footer>
  </main>
</div>
{spy}
{THEME_JS}</body>
</html>
"""
    for bad in ("\u2014", "\u2013"):
        if bad in page_html:
            raise SystemExit(f"web: dash character {bad!r} in the page; use a comma, colon or ' -- '")
    return page_html


def main():
    ap = argparse.ArgumentParser(description="render a sheet source as an Interactive Whitepaper (one HTML file)")
    ap.add_argument("src")
    ap.add_argument("-o", "--out")
    ap.add_argument("-s", "--set", action="append", default=[], metavar="KEY=VALUE",
                    help="front-matter field, over the file's own")
    a = ap.parse_args()
    out = Path(a.out or Path(a.src).with_suffix(".html")).resolve()
    out.write_text(render(a.src, a.set))
    print(out)


if __name__ == "__main__":
    main()
