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
Parts (# and :::part) group the rail and number sections II.3; a status= on a heading becomes a pill and a rail
dot; a diagram node's link= is clickable; a :::trace becomes a scrubber over its steps; a :::glossary gives the
first use of each term a card.

The page shell is the Interactive Whitepaper template, web-template.html beside this file, or SHEET_TEMPLATE.
"""
import argparse
import base64
import html
import os
import sys
import re
import urllib.parse
from pathlib import Path

import handbook
import sheet

TEMPLATE = Path(os.environ.get("SHEET_TEMPLATE", Path(__file__).resolve().parent / "web-template.html"))
handbook.STYLE["svg.fonttype"] = "path"          # lettering as outlines: exact, and nothing for the page to fetch
handbook.LINK_NODES = True                       # a diagram node's link= becomes a clickable region here

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
/* numbers come from the source, so paper and screen agree (II.3, Fig. II.3.1) */
.chapter>h2[data-n]::before{content:attr(data-n) "\\00a0\\00a0"}
h3[data-n]::before{content:attr(data-n) "\\00a0\\00a0"}
.cap[data-n]::before{content:"Fig. " attr(data-n) " -- "}
caption[data-n]::before{content:"Table " attr(data-n) " -- "}
/* parts */
section.part{margin:4.5rem 0 1rem;padding-top:1.4rem;border-top:3px solid var(--slate)}
section.part .part-no{font-family:var(--sans);font-size:.72rem;font-weight:700;letter-spacing:.22em;text-transform:uppercase;
  color:var(--slate);margin:0}
section.part>h2{font-size:2.1rem;font-weight:600;line-height:1.15;margin:.25rem 0 .7rem;text-wrap:balance}
section.part .thesis{font-style:italic;font-size:1.14rem;line-height:1.55;color:var(--ink-2);max-width:40rem;margin:0 0 1rem}
.part-list{list-style:none;padding:0;margin:1.2rem 0 0;border-top:1px solid var(--rule)}
.part-list li{display:flex;align-items:center;gap:.8rem;padding:.42rem 0;border-bottom:1px solid var(--rule)}
.part-list a{flex:1;display:flex;gap:.8rem;text-decoration:none;color:var(--ink);font-family:var(--sans);font-size:.92rem}
.part-list a:hover .t{color:var(--slate)}
.part-list .n{color:var(--ink-3);min-width:3.2rem;font-variant-numeric:tabular-nums}
/* status: a pill on the heading, a dot in the rail */
.pill.st-built{color:var(--ok)} .pill.st-prototyped{color:var(--slate)}
.pill.st-designed{color:var(--warn)} .pill.st-speculative{color:var(--ink-3);border-style:dashed}
h2 .pill,h3 .pill,h4 .pill{vertical-align:middle;margin-left:.75rem;font-size:.6rem;position:relative;top:-.12em}
.sd{display:inline-block;width:.46rem;height:.46rem;border-radius:50%;background:currentColor;margin-left:.45rem;
  vertical-align:middle;flex:none}
.sd.st-built{color:var(--ok)} .sd.st-prototyped{color:var(--slate)} .sd.st-designed{color:var(--warn)}
.sd.st-speculative{color:var(--ink-3);background:none;border:1px dashed currentColor;width:.36rem;height:.36rem}
.legend{display:flex;flex-wrap:wrap;gap:.35rem .9rem;margin:0 0 .8rem;font-size:.72rem;color:var(--ink-3)}
.legend .sd{margin:0 .3rem 0 0}
.rail nav a{display:flex;align-items:baseline}
.rail nav a .n{flex:none}
.rail nav a .t{flex:0 1 auto}
.rail nav a .sd{flex:none;align-self:center}
.rail nav li.part>a{color:var(--ink);font-weight:600;margin-top:.55rem}
.rail nav li.part>a .n{color:var(--slate)}
.rail nav ol.sub{list-style:none;margin:0;padding:0;columns:auto}
@media (min-width:72.01rem){.rail{max-height:calc(100vh - 3rem);overflow-y:auto;scrollbar-width:thin;padding-right:.4rem}}
/* the trace: every step listed without script and on paper; the script makes it a scrubber */
.trace-fig{margin:1.8rem 0}
.trace-steps{margin:0;padding-left:1.4rem}
.trace-steps li{margin:.5rem 0}
.trace-steps .k{font-family:var(--sans);font-weight:600;font-size:.9rem;color:var(--slate)}
.trace-steps p{margin:.15rem 0 0}
.trace .see{font-family:var(--sans);font-size:.78rem}
.trace.js .trace-steps{display:none}
.trace .ctl{display:flex;align-items:center;gap:.6rem;margin:.1rem 0 .9rem}
.trace .ctl input[type=range]{flex:1;margin:0}
.trace .ctl button{font-family:var(--sans);font-size:.78rem;background:none;border:1px solid var(--rule-2);color:var(--ink-2);
  border-radius:2px;padding:.2rem .6rem;cursor:pointer}
.trace .ctl button:hover{color:var(--ink);border-color:var(--slate)}
.trace .ctl .pos{font-family:var(--sans);font-size:.78rem;color:var(--ink-3);font-variant-numeric:tabular-nums;min-width:3.2rem;text-align:right}
.trace .lane .span{font-size:.7rem;padding:0 .3rem;text-align:center;line-height:1.15;overflow:hidden}
.trace .lane .span.cur{color:var(--paper)}
.trace .lane .span.past{background:color-mix(in srgb,var(--slate) 22%,var(--paper));color:var(--ink-2)}
.trace .readout .k{font-family:var(--sans);font-size:.95rem}
.trace .readout p{font-size:1rem;max-width:42rem}
@media print{.trace.js .trace-steps{display:block}.trace .lane,.trace .ctl,.trace .readout{display:none}}
/* diagram nodes that link: the box lights on hover and focus */
a.node-link{cursor:pointer}
a.node-link path.hit{fill:var(--slate);fill-opacity:0;stroke:none}
a.node-link:hover path.hit,a.node-link:focus-visible path.hit{fill-opacity:.16}
a.node-link:focus-visible path.hit{stroke:var(--slate);stroke-width:2px}
a.node-link:focus{outline:none}
/* glossary: dotted terms, one card */
a.term{color:inherit;text-decoration:underline dotted var(--slate);text-underline-offset:.2em;text-decoration-thickness:1.5px;cursor:help}
a.term:hover,a.term[aria-expanded="true"]{color:var(--slate)}
dl.glossary{display:grid;grid-template-columns:minmax(8rem,max-content) 1fr;gap:.45rem 1.2rem;margin:1.2rem 0}
dl.glossary dt{font-family:var(--sans);font-weight:600;font-size:.9rem;color:var(--ink)}
dl.glossary dd{margin:0;color:var(--ink-2)}
dl.glossary dt:target,dl.glossary dt:target+dd{background:var(--slate-soft)}
#gcard{position:absolute;z-index:20;max-width:22rem;background:var(--paper);color:var(--ink-2);border:1px solid var(--rule-2);
  border-top:2px solid var(--slate);box-shadow:0 6px 18px rgba(0,0,0,.18);padding:.6rem .8rem;font-size:.9rem;line-height:1.5}
#gcard .gt{display:block;font-family:var(--sans);font-size:.72rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--slate);margin-bottom:.2rem}
#gcard .gp{display:block;font-family:var(--sans);font-size:.68rem;color:var(--ink-3);margin-top:.35rem}
#gcard[hidden]{display:none}
@media (max-width:40rem){dl.glossary{grid-template-columns:1fr}dl.glossary dd{margin-bottom:.5rem}}
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

PAGE_JS = """<script>
(function(){
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  // ---- traces: the step list becomes a lane, a slider and a readout ----
  Array.prototype.forEach.call(document.querySelectorAll('[data-trace]'), function(tr, ti){
    var steps = Array.prototype.map.call(tr.querySelectorAll('.trace-steps > li'), function(li){
      var see = li.querySelector('a.see');
      return { k: li.querySelector('.k').innerHTML, p: li.querySelector('p').innerHTML,
               href: see ? see.getAttribute('href') : null, see: see ? see.innerHTML : '' };
    });
    if (!steps.length) return;
    var id = 'tr' + ti;
    var lane = document.createElement('div');
    lane.className = 'lane'; lane.setAttribute('role', 'group'); lane.setAttribute('aria-label', 'Steps');
    var ctl = document.createElement('div'); ctl.className = 'ctl';
    ctl.innerHTML = '<button type="button" data-d="-1" aria-label="Previous step">Prev</button>' +
      '<input type="range" min="0" max="' + (steps.length - 1) + '" value="0" step="1" aria-label="Step" aria-describedby="' + id + '-ro">' +
      '<button type="button" data-d="1" aria-label="Next step">Next</button><span class="pos" aria-hidden="true"></span>';
    var ro = document.createElement('div');
    ro.className = 'readout'; ro.id = id + '-ro'; ro.setAttribute('aria-live', 'polite');
    ro.innerHTML = '<p class="lbl"></p><span class="k"></span><p class="tx"></p><a class="ref see"></a>';
    var range = ctl.querySelector('input'), pos = ctl.querySelector('.pos');
    steps.forEach(function(st, i){
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'span'; b.textContent = i + 1;
      b.setAttribute('aria-label', 'Step ' + (i + 1));
      b.addEventListener('click', function(){ range.value = i; show(); });
      lane.appendChild(b);
    });
    function show(){
      var cur = +range.value, st = steps[cur];
      Array.prototype.forEach.call(lane.children, function(b, i){
        b.classList.toggle('cur', i === cur); b.classList.toggle('past', i < cur);
        b.setAttribute('aria-current', i === cur ? 'step' : 'false');
      });
      ro.querySelector('.lbl').textContent = 'Step ' + (cur + 1) + ' of ' + steps.length;
      ro.querySelector('.k').innerHTML = st.k;
      ro.querySelector('.tx').innerHTML = st.p;
      var a = ro.querySelector('a.see');
      if (st.href){ a.hidden = false; a.setAttribute('href', st.href); a.innerHTML = 'See ' + st.see; } else { a.hidden = true; }
      pos.textContent = (cur + 1) + ' / ' + steps.length;
      ctl.querySelector('[data-d="-1"]').disabled = cur === 0;
      ctl.querySelector('[data-d="1"]').disabled = cur === steps.length - 1;
    }
    ctl.addEventListener('click', function(e){
      var d = e.target.getAttribute && e.target.getAttribute('data-d');
      if (!d) return;
      range.value = Math.max(0, Math.min(steps.length - 1, +range.value + +d)); show();
    });
    range.addEventListener('input', show);
    tr.appendChild(lane); tr.appendChild(ctl); tr.appendChild(ro);
    tr.classList.add('js');
    show();
  });

  // ---- glossary: a card on hover or focus, pinned by a click, closed with Esc ----
  var card = document.createElement('div');
  card.id = 'gcard'; card.setAttribute('role', 'tooltip'); card.hidden = true;
  document.body.appendChild(card);
  var pinned = null;
  function open(t){
    var id = t.getAttribute('href').slice(1), dt = document.getElementById(id);
    if (!dt) return;
    card.innerHTML = '<span class="gt">' + dt.innerHTML + '</span>' + dt.nextElementSibling.innerHTML +
      '<span class="gp">' + (pinned === t ? 'Pinned. Esc to close.' : 'Click to pin.') + '</span>';
    card.hidden = false;
    var r = t.getBoundingClientRect(), w = Math.min(352, document.documentElement.clientWidth - 24);
    card.style.maxWidth = w + 'px';
    var left = Math.max(12, Math.min(r.left + window.scrollX, window.scrollX + document.documentElement.clientWidth - w - 12));
    card.style.left = left + 'px';
    card.style.top = (r.bottom + window.scrollY + 6) + 'px';
    t.setAttribute('aria-describedby', 'gcard');
  }
  function close(){
    card.hidden = true;
    if (pinned){ pinned.setAttribute('aria-expanded', 'false'); pinned = null; }
  }
  Array.prototype.forEach.call(document.querySelectorAll('a.term'), function(t){
    t.setAttribute('aria-expanded', 'false');
    t.addEventListener('mouseenter', function(){ if (!pinned) open(t); });
    t.addEventListener('mouseleave', function(){ if (!pinned) card.hidden = true; });
    t.addEventListener('focus', function(){ if (!pinned) open(t); });
    t.addEventListener('blur', function(){ if (!pinned) card.hidden = true; });
    t.addEventListener('click', function(e){
      e.preventDefault();
      if (pinned === t){ close(); return; }
      if (pinned) pinned.setAttribute('aria-expanded', 'false');
      pinned = t; t.setAttribute('aria-expanded', 'true'); open(t);
    });
  });
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape') close(); });
  document.addEventListener('click', function(e){
    if (pinned && !card.contains(e.target) && e.target !== pinned) close();
  });

  // ---- the rail follows the reader when it scrolls on its own ----
  var rail = document.querySelector('.rail');
  var toc = document.getElementById('toc');
  if (rail && toc && 'MutationObserver' in window){
    new MutationObserver(function(ms){
      ms.forEach(function(m){
        var a = m.target;
        if (a.getAttribute('aria-current') !== 'true' || rail.scrollHeight <= rail.clientHeight + 4) return;
        var top = a.offsetTop - rail.clientHeight / 3;
        rail.scrollTo({ top: top, behavior: reduce ? 'auto' : 'smooth' });
      });
    }).observe(toc, { attributes: true, subtree: true, attributeFilter: ['aria-current'] });
  }
})();
</script>
"""


slug = sheet.slug
STATUS_PILL = {"built": "built", "prototyped": "prototyped", "designed": "designed", "speculative": "speculative"}


def pill(status):
    return f'<span class="pill st-{status}">{status}</span>' if status else ""


def dot(status):
    return f'<span class="sd st-{status}" title="{status}" aria-label="{status}"></span>' if status else ""


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


NODELINK = re.compile(r'<a xlink:href="nvlink:([\w.-]+):([^"]*)">\s*<path(.*?)style="[^"]*"\s*/>\s*</a>', re.S)


def node_links(svg):
    """a diagram node with link=: its hit region becomes a real link, focusable, lit on hover"""
    def one(m):
        a, label = m.group(1), urllib.parse.unquote(m.group(2)).title()
        _LINKS.append((label, a))
        return (f'<a class="node-link" href="#{a}" aria-label="{html.escape(label)}"><title>{html.escape(label)}</title>'
                f'<path class="hit"{m.group(3)}/></a>')
    return NODELINK.sub(one, svg)


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
        self.chapnum = "0"
        self.figs = self.tabs = self.eqs = 0
        self.gloss = []                             # (term, definition, anchor) for the hover cards
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
        h = self.next_head(level, text)
        if h["level"] == 0:
            self.m["title"] = h["text"]
            return ""
        a, text = h["id"], h["text"]
        if level == 1:
            self.cur_part = h["part"]
            self.ids[a] = f"Part {h['num']}"
            return f"\x01P\x1f{a}\x1f{h['num']}\x1f\x1f{inline(text.rstrip('.'))}\x01"
        if level == 2:
            self.chap += 1
            self.chapnum = h["num"]
            self.figs = self.tabs = self.eqs = 0
            self.ids[a] = f"&sect;{h['num']}"
            return f"\x01C\x1f{a}\x1f{h['num']}\x1f{h['status'] or ''}\x1f{inline(text.rstrip('.'))}\x01"
        if level == 3:
            self.ids[a] = f"&sect;{h['num']}"
            return f'<h3 id="{a}" data-n="{h["num"]}">{inline(text.rstrip("."))}{pill(h["status"])}</h3>'
        return f'<h{level} id="{a}">{inline(text.rstrip("."))}{pill(h["status"])}</h{level}>'

    def figure(self, body, caption, width=""):
        self.figs += 1
        n = f"{self.chapnum}.{self.figs}"
        a, label = f"fig-{n}", f"Fig. {n}"
        self.ids[a] = label
        self.items.append((a, label, caption))
        plate = "<image" in body or "<img" in body
        if body.lstrip().startswith("<svg"):
            body = sheet.private_ids(clean_svg(body))
            body = sized(body) if plate else retint(sized(body))
            body = node_links(body)
        cls = "fig scroll plate" if plate else "fig scroll"
        return (f'<figure class="{cls}" id="{a}"><div class="art">{body}</div>'
                f'<figcaption class="cap" data-n="{n}">{inline(caption) if caption else ""}</figcaption></figure>')

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
            n = f"{self.chapnum}.{self.tabs}"
            a, label = f"tab-{n}", f"Table {n}"
            self.ids[a] = label
            self.items.append((a, label, caption))
            idattr, cap = f' id="{a}"', f'<caption data-n="{n}">{inline(caption)}</caption>'
        th = "".join(f"<th>{inline(c)}</th>" for c in head)
        tr = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
        return f'<div class="scroll"{idattr}><table>{cap}<thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'

    def eqno(self):
        self.eqs += 1
        return f'<span class="eqno">({self.chapnum}.{self.eqs})</span>'

    def trace(self, caption, body):
        """all the steps as a list (no script, print); the script adds the lane, the slider and the readout"""
        self.figs += 1
        n = f"{self.chapnum}.{self.figs}"
        a, label = f"fig-{n}", f"Fig. {n}"
        self.ids[a] = label
        self.items.append((a, label, caption))
        lis = []
        for lab, txt, ref in self.trace_steps(body):
            see = ""
            if ref:
                _LINKS.append((lab, ref))
                see = f'<a class="ref see" href="#{ref}">\x05{ref}\x05</a>'
            lis.append(f'<li><span class="k">{inline(lab)}</span><p>{inline(txt)}</p>{see}</li>')
        return (f'<figure class="trace-fig" id="{a}"><div class="trace" data-trace>'
                f'<ol class="trace-steps">{"".join(lis)}</ol></div>'
                f'<figcaption class="cap" data-n="{n}">{inline(caption) if caption else ""}</figcaption></figure>')

    def loop(self, arg, body):
        """an agent loop: the graph laid out, its run replayed, state beside it (loopgraph.js)"""
        cap, g = sheet.loop_source(arg, body, self.base)
        self.loops += 1
        self.figs += 1
        n = f"{self.chapnum}.{self.figs}"
        a, label = f"fig-{n}", f"Fig. {n}"
        self.ids[a] = label
        self.items.append((a, label, cap))
        return (f'<figure class="lg" data-loopgraph id="{a}"><script type="application/json">{g}</script>'
                f'<figcaption class="cap" data-n="{n}">{inline(cap) if cap else ""}</figcaption></figure>')

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
        if kind == "trace":
            return self.trace(arg, body)
        if kind == "loop":
            return self.loop(arg, body)
        if kind == "glossary":
            terms = self.glossary_terms(body)
            items = []
            for t, d in terms:
                a = "gl-" + (slug(t) or "term")
                self.gloss.append((t, d, a))
                items.append(f'<dt id="{a}">{inline(t)}</dt><dd>{inline(d)}</dd>')
            return f'<dl class="glossary">{"".join(items)}</dl>'
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


def chapters(content, meta, page):
    """split at the heading markers into parts and chapters; anything before the first is the abstract.
    toc: a list of (anchor, title, num, status, children) where children are chapters inside a part"""
    bits = re.split(r"\x01([^\x01]*)\x01", content)
    head, rest = bits[0], bits[1:]
    out, toc = [], []
    lead = (f"<p>{inline(str(meta['abstract']))}</p>" if meta.get("abstract") else "") + head.strip()
    if lead.strip():
        out.append(f'<section id="abstract" class="abstract" aria-labelledby="abstract-h">'
                   f'<span class="lbl" id="abstract-h">Abstract</span>{lead}</section>')
        toc.append(("abstract", "Abstract", "", "", None))
    for i in range(0, len(rest), 2):
        kind, a, num, status, title = rest[i].split("\x1f", 4)
        body = rest[i + 1]
        plain = re.sub(r"<[^>]+>", "", title)
        if kind == "P":
            idx = next(h["part"] for h in page.heads if h["id"] == a)
            thesis = f'<p class="thesis">{inline(page.thesis[idx])}</p>' if idx in page.thesis else ""
            kids = [c for c in page.part_list(idx)]
            lst = "".join(f'<li><a href="#{c["id"]}"><span class="n">{c["num"]}</span><span class="t">{inline(c["text"])}</span></a>'
                          f'{pill(c["status"])}</li>' for c in kids)
            out.append(f'<section class="part" id="{a}" aria-labelledby="{a}-h"><p class="part-no">Part {num}</p>'
                       f'<h2 id="{a}-h">{title}</h2>{thesis}{body}'
                       + (f'<ol class="part-list">{lst}</ol>' if lst else "") + "</section>")
            toc.append((a, plain, num, "", []))
        else:
            out.append(f'<section class="chapter" id="{a}" aria-labelledby="{a}-h">'
                       f'<h2 id="{a}-h" data-n="{num}">{title}{pill(status)}</h2>{body}</section>')
            entry = (a, plain, num, status, None)
            if toc and toc[-1][4] is not None:
                toc[-1][4].append(entry)
            else:
                toc.append(entry)
    return "\n".join(out), toc


def rail(page, toc, meta, status):
    def item(a, t, n, st, kids):
        sub = ""
        if kids:
            sub = '<ol class="sub">' + "".join(item(*k) for k in kids) + "</ol>"
        cls = ' class="part"' if kids is not None else ""
        num = f'<span class="n">{n}</span>' if n else ""
        return f'<li{cls}><a href="#{a}">{num}<span class="t">{t}</span>{dot(st)}</a>{sub}</li>'
    li = "\n".join("        " + item(*e) for e in toc)
    used = {st for e in toc for st in [e[3]] + [k[3] for k in (e[4] or [])] if st}
    legend = ""
    if used:
        legend = ('      <div class="legend" aria-label="Status key">'
                  + "".join(f"<span>{dot(st)}{st}</span>" for st in sheet.STATUSES if st in used) + "</div>\n")
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
{legend}      <button class="theme-btn" id="theme-btn" type="button">Light / dark</button>
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


SKIP_TAGS = {"a", "h1", "h2", "h3", "h4", "h5", "h6", "code", "pre", "svg", "script", "style", "dt", "dd", "caption",
             "figcaption", "button", "title", "dl"}


def glossary_terms(content, gloss):
    """the first use of each glossary term in running text: a link to its entry that the script turns into a card"""
    if not gloss:
        return content
    left = sorted(gloss, key=lambda g: -len(g[0]))
    pats = {g[2]: re.compile(r"(?<![\w-])" + re.escape(html.escape(g[0], quote=False)) + r"(?![\w-])", re.I) for g in gloss}
    out, depth = [], {}
    for tok in re.split(r"(<[^>]+>)", content):
        if tok.startswith("<"):
            m = re.match(r"<(/?)([a-zA-Z0-9]+)", tok)
            if m and m.group(2).lower() in SKIP_TAGS and not tok.endswith("/>"):
                t = m.group(2).lower()
                depth[t] = depth.get(t, 0) + (-1 if m.group(1) else 1)
            out.append(tok)
            continue
        if not left or any(v > 0 for v in depth.values()):
            out.append(tok)
            continue
        while left:
            hits = [(m.start(), -len(m.group(0)), g, m) for g in left if (m := pats[g[2]].search(tok))]
            if not hits:
                break
            _, _, g, m = min(hits, key=lambda h: (h[0], h[1]))
            left.remove(g)
            out.append(tok[:m.start()])
            out.append(f'<a class="term" href="#{g[2]}">{m.group(0)}</a>')
            tok = tok[m.end():]
        out.append(tok)
    return "".join(out)


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
    page.prepare(body.splitlines())
    content, toc = chapters(page.blocks(body.splitlines()), meta, page)
    content = re.sub("\x05([\\w.-]+)\x05", lambda m: page.ids.get(m.group(1)) or sys.exit(
        f"web: trace step links to #{m.group(1)}, which is not in the document"), content)
    content = glossary_terms(content, page.gloss)
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
{THEME_JS}{PAGE_JS}{sheet.loop_assets() if page.loops else ""}</body>
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
