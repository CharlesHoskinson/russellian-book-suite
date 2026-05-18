"""Inject a chapter-heading CSS override at the very end of the <head>
to win against Tailwind's preflight reset.
"""
import sys
from pathlib import Path

HEADING_CSS = """
<style id="chapter-headings-override">
/* Override Tailwind preflight that resets heading font-size/weight to inherit. */
h1, h2, h3, h4, h5, h6 {
  font-family: Georgia, "Times New Roman", "Iowan Old Style", serif !important;
  color: #1a1a1a !important;
  line-height: 1.2 !important;
}

/* Chapter heading (h1 from `# Chapter N: Title`). */
h1 {
  font-size: 2.0em !important;
  font-weight: 700 !important;
  margin: 1.8em 0 0.8em 0 !important;
  padding-bottom: 0.3em !important;
  border-bottom: 1px solid #b08d57 !important;
  letter-spacing: -0.01em !important;
}

/* Top-level title at the very start of the book (the `# Life in Bermuda` line). */
body > h1:first-of-type,
.markdown-content > h1:first-of-type,
article > h1:first-of-type,
main > h1:first-of-type {
  font-size: 2.6em !important;
  text-align: center;
  border-bottom: none !important;
  margin: 0.5em 0 0.2em 0 !important;
}

/* Section heading. */
h2 {
  font-size: 1.45em !important;
  font-weight: 700 !important;
  margin: 1.8em 0 0.5em 0 !important;
  color: #2b2b2b !important;
  font-variant: normal !important;
}

/* Subsection heading. */
h3 {
  font-size: 1.15em !important;
  font-weight: 700 !important;
  font-style: italic !important;
  margin: 1.4em 0 0.4em 0 !important;
  color: #444 !important;
}

h4 {
  font-size: 1.0em !important;
  font-weight: 700 !important;
  margin: 1.0em 0 0.3em 0 !important;
}

/* Footnotes endnote heading rendered as h2 inside section.footnotes — make it small. */
section.footnotes h2 {
  font-size: 0.95em !important;
  font-weight: 700 !important;
  font-variant: small-caps !important;
  letter-spacing: 0.08em !important;
  color: #555 !important;
  margin: 0 0 0.6em 0 !important;
  border: none !important;
}

/* Print page-break rules. */
@media print {
  h1 {
    page-break-before: always;
    break-before: page;
    page-break-after: avoid;
    break-after: avoid-page;
  }
  body > h1:first-of-type,
  .markdown-content > h1:first-of-type,
  article > h1:first-of-type,
  main > h1:first-of-type {
    page-break-before: avoid;
    break-before: avoid;
  }
  h2, h3, h4 {
    page-break-after: avoid;
    break-after: avoid-page;
  }
}
</style>
"""

REL = Path("C:/bermuda-manual/book/releases/3.0.0")
HTML = REL / "manuscript.html"
text = HTML.read_text(encoding="utf-8")

# Inject just before </head> so it wins the cascade.
text = text.replace("</head>", HEADING_CSS + "\n</head>", 1)
HTML.write_text(text, encoding="utf-8")
print(f"manuscript.html: {len(text):,} bytes (heading override injected)")

# Re-render PDF
sys.path.insert(0, str(Path("C:/Users/charl/.claude/skills/book-compose")))
from scripts.print_pdf import print_pdf
pdf = REL / "manuscript.pdf"
print_pdf(HTML, pdf)
print(f"manuscript.pdf: {pdf.stat().st_size:,} bytes")

from pypdf import PdfReader
pages = len(PdfReader(str(pdf)).pages)
print(f"pages = {pages}")
