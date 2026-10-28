"""Renders every snippet in CATALOG.md onto one sheet, so the catalog cannot drift from the code.
  python catalog_check.py [-o out.pdf]             (default: catalog-check.pdf in the system temp directory)"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("-o", "--out", default=str(Path(tempfile.gettempdir()) / "catalog-check.pdf"))
a = ap.parse_args()

text = (HERE / "CATALOG.md").read_text()
snippets = [m for m in re.findall(r"```\n(.*?)```", text, re.S) if m.lstrip().startswith(":::")]
body = ["---", "title: Catalog check", "section: C", "tab: CAT", "date: 10.28.2026", "---", ""]
for k, snip in enumerate(snippets, 1):
    body += [f"### Snippet {k}", "", snip.rstrip(), ""]
with tempfile.NamedTemporaryFile("w", suffix=".md", dir=HERE, delete=False) as fh:      # beside, so paths resolve
    fh.write("\n".join(body))
    src = Path(fh.name)
try:
    r = subprocess.run([sys.executable, str(HERE / "sheet.py"), str(src), "-o", a.out], capture_output=True, text=True)
finally:
    src.unlink()
if r.returncode:
    sys.exit(f"catalog check failed:\n{r.stderr or r.stdout}")
print(f"{len(snippets)} snippets rendered: {a.out}")
