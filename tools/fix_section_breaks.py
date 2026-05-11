"""Post-process the assembled manuscript so every closing </section> is
followed by a blank line, ensuring the next markdown block parses correctly.
Also re-applies the same to </div> blocks (the hero-table wrappers).
"""
import re
import sys
from pathlib import Path

REL = Path("C:/bermuda-manual/book/releases/3.0.0")
MD = REL / "manuscript.md"
HTML = REL / "manuscript.html"

text = MD.read_text(encoding="utf-8")

# Add blank line after </section> when next non-blank line starts with # heading
text = re.sub(r"(</section>)\s*\n([^\n])", r"\1\n\n\2", text)
# Same for </div> closing hero-table wrappers
text = re.sub(r"(</div>)\s*\n(#{1,6}\s)", r"\1\n\n\2", text)

MD.write_text(text, encoding="utf-8")
print(f"manuscript.md fixed ({len(text):,} bytes)")

# Update HTML in place — swap the manuscript body inside the script tag
html = HTML.read_text(encoding="utf-8")
MANUSCRIPT_RE = re.compile(
    r'(<script id="book-manuscript" type="text/markdown">)(.*?)(</script>)',
    re.DOTALL,
)
html_new = MANUSCRIPT_RE.sub(lambda m: m.group(1) + text + m.group(3), html, count=1)
HTML.write_text(html_new, encoding="utf-8")
print(f"manuscript.html updated ({len(html_new):,} bytes)")

sys.path.insert(0, str(Path("C:/Users/charl/.claude/skills/book-compose")))
from scripts.print_pdf import print_pdf
pdf = REL / "manuscript.pdf"
print_pdf(HTML, pdf)
print(f"manuscript.pdf: {pdf.stat().st_size:,} bytes")

from pypdf import PdfReader
print(f"pages = {len(PdfReader(str(pdf)).pages)}")
