"""v4.3 finalization: rebuild release + footnote post-process + new prose-furniture CSS
+ For Further Reading section + React merge + PDF render.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path("C:/Users/charl/.claude/skills/book-compose")))

from scripts.build_release_bundle import build_release_bundle
from scripts.build_book import build_book
from scripts.print_pdf import print_pdf

WS = Path("C:/bermuda-manual")
REL = WS / "book" / "releases" / "3.0.0"
V1 = WS / "book" / "releases" / "1.0.0" / "manuscript.html"

# 1. Rebuild chapter bundles
for n in range(1, 11):
    build_release_bundle(WS, f"ch-{n:02d}", version="v3-final", formats=["markdown"])
print("chapter bundles rebuilt")

# 2. Build book release 3.0.0
chapter_versions = {f"ch-{n:02d}": "v3-final" for n in range(1, 11)}
build_book(WS, version="3.0.0", chapter_versions=chapter_versions,
           book_title="Life in Bermuda", book_id="bermuda-manual")
print("book release 3.0.0 rebuilt")

MD = REL / "manuscript.md"
HTML = REL / "manuscript.html"

# 3. Strip any stray clm tokens
CLM_RE = re.compile(r"\s*\[clm-\d{4}-\d{6}\]")
text = MD.read_text(encoding="utf-8")
text = CLM_RE.sub("", text)
text = re.sub(r"  +", " ", text)
text = re.sub(r" ([.,;:!?])", r"\1", text)

# 4. Process GFM footnotes -> HTML
sys.path.insert(0, "C:/tmp")
from process_footnotes import process_manuscript
text = process_manuscript(text)
fn_count = text.count('class="footnote-ref"')
print(f"footnotes inlined: {fn_count}")

# 5. Front + back matter
PREFACE = """\
## Preface

This manual gives a working picture of contemporary Bermuda for the reader who needs more than tourist copy and less than a doctoral thesis. It covers the geography that produced the place, the history that shaped its institutions, the government that runs it now, the economy that pays for it, the people who live in it, the practical question of what living there costs, the rules that govern who may live there at all, the school system that raises a child through to college, the hospital that treats them, and the ways they get around.

The chapters are written as argument-bearing prose anchored in concrete scenes. Where data are clearer in a chart or a table, you will find the chart or the table. Where a term needs a one-sentence gloss, the gloss appears in a sidebar rather than as a parenthetical interruption of the sentence. Where a claim has a nuance or a contested source, the nuance lives in a footnote.

Numeric claims trace to the sources collected at the back. Where two sources disagreed, the dispute is noted in the prose rather than papered over. Where a source was thin, the prose says so.

The manual is short by design. A reader should be able to finish it in an evening and feel they understand the place well enough to talk about it.

## How the chapters are arranged

The first three chapters set the frame: the islands themselves, the history that turned them into a colony and a colony into a self-governing territory, and the government and legal system that runs the place today. The fourth chapter explains where the money comes from and what that money has done to the economy. The fifth describes the people. The sixth tells you what it costs to live there day to day, and the seventh tells you whether you may even live there at all. The last three chapters cover education, healthcare, and the practical questions of moving around and what people do with their time.

---

"""

GLOSSARY = (Path("C:/tmp/glossary_v4_3.md").read_text(encoding="utf-8")
            if Path("C:/tmp/glossary_v4_3.md").exists()
            else """\
## Glossary

**AC50.** A class of foiling fifty-foot catamarans designed for the 2017 America's Cup, raced in Bermuda's Great Sound.

**African Methodist Episcopal Church (AME).** Historically Black denomination present in Bermuda since the nineteenth century.

**Annual Rental Value (ARV).** The notional annual rent of a property, used as the base for Bermuda's land tax and as the threshold for several immigration and housing rules.

**Bermuda cedar.** *Juniperus bermudiana*, a juniper endemic to Bermuda, called "cedar" in local usage.

**Bermuda dollar (BMD).** Bermuda's currency, pegged at parity with the US dollar; both circulate interchangeably.

**Bermuda Hospitals Board (BHB).** The statutory body that runs King Edward VII Memorial Hospital and the Mid-Atlantic Wellness Institute.

**Bermuda Monetary Authority (BMA).** The financial regulator and currency authority, established 1969.

**Bermudian status.** The legal category of full Bermudian citizenship, which carries the right to live, work, and own property without restriction.

**British Overseas Territory.** Constitutional status of Bermuda since 2002 (formerly Crown Colony); a self-governing territory under the British Crown.

**Captive insurer.** An insurance company set up to insure the risks of its parent group rather than to write outside business.

**Cistern.** Underground rainwater storage required for every Bermuda house.

**Common law.** The English-inherited body of judge-made law that, alongside Bermudian statutes, forms the basis of Bermuda's legal system.

**Constitution Order 1968.** The instrument that established Bermuda's current constitutional framework.

**Cup Match.** The two-day cricket holiday between the Somerset and St. George's clubs, held in late July or early August.

**FutureCare.** Bermuda's public health insurance plan for residents aged 65 and over.

**HIP (Health Insurance Plan).** The basic public health insurance product administered by the Bermuda Health Council.

**KEMH.** King Edward VII Memorial Hospital, the islands' main acute-care hospital.

**L. F. Wade International Airport.** Bermuda's only commercial airport, on St. David's Island in St. George's Parish.

**Mid-Atlantic Wellness Institute (MWI).** Bermuda's psychiatric and intellectual-disability hospital.

**OECD Pillar Two.** The international agreement imposing a 15 per cent minimum corporate tax on large multinationals.

**Privy Council.** The Judicial Committee of the Privy Council in London, the final court of appeal for Bermuda.

**Reinsurance.** Insurance for insurers; the dominant export industry of Bermuda's international business sector.

**Sea Venture.** The English ship wrecked on Bermuda's outer reef in July 1609, leading to the settlement of the islands.

""")

SOURCES = """\
## Sources

This manual draws on a collection of primary source documents prepared during research. Where the prose makes a numeric claim, the relevant source is listed below.

1. **cost-of-living** — Numbeo aggregate cost-of-living survey for Bermuda (retrieved March 2026).
2. **culture** — Bermuda National Trust and Department of Culture briefings on Cup Match, Bermuda Day, Gombey troupes, and the religious calendar.
3. **demographics** — Bermuda Department of Statistics 2016 Census and inter-census updates through 2024.
4. **economy** — Bermuda Monetary Authority annual reports, Ministry of Finance budget statements, and OECD Pillar Two country notes.
5. **education** — Ministry of Education annual statistical digest; Bermuda College registrar's office; private school directories.
6. **geography** — Department of Conservation Services briefings, Bermuda Aquarium Museum & Zoo factsheets, and the original Norwood survey records.
7. **government** — Bermuda Constitution Order 1968 and subsequent amendments; Cabinet Office structure documents.
8. **healthcare** — Bermuda Health Council annual reports and Bermuda Hospitals Board briefings.
9. **history** — Academic and primary-source accounts of the Sea Venture, the early colonial period, slavery, emancipation, the 1968 constitutional settlement, and twentieth-century political history.
10. **overview** — General-reference compilation cross-checked against other sources.
11. **recent-developments** — News reporting from The Royal Gazette and Bernews on 2024–2026 policy changes.
12. **tourism** — Bermuda Tourism Authority arrivals data and the Ministry of Tourism strategic plan.
13. **transportation** — Department of Public Transportation route briefings; Marine and Ports ferry schedules.

The parish map is rendered from OpenStreetMap administrative boundaries (© OpenStreetMap contributors, ODbL).
"""

READING_GUIDE = """\
## How to read this manual

This is a manual for somebody who wants to understand Bermuda, not a brochure for someone considering a visit. Read it the way you might read a country handbook: cover to cover for orientation, then back to whichever chapter the present moment is asking about.

If you are deciding whether to move there, start with Chapter 7 (Housing and Immigration) and then Chapter 6 (Daily Life and Cost of Living). Those two chapters will tell you whether the move is plausible at all. Chapter 4 (Economy) explains the kind of work that brings people in. Chapter 9 (Healthcare) and Chapter 8 (Education) cover the two big questions families ask next.

If you are reading the manual as background for a business or investment decision, start with Chapter 4 (Economy) and Chapter 3 (Government and Legal System).

If you are reading for general curiosity, start with Chapter 1 (Introduction and Geography) and Chapter 2 (History). The geography produced the history, and the history produced everything else.

## A note on numbers

The manual cites numbers conservatively. Where sources disagreed, the prose follows the canonical-facts document adopted during preparation. Population figures are based on the 2016 Census plus the 2024 inter-census update.

Currency figures are quoted in Bermuda dollars, which trade at parity with the US dollar.

## What this manual does not cover

The manual does not attempt to be a tourist guide, a travel writing essay, a policy brief, or a partisan account of Bermudian politics.

It does not offer recommendations on where to stay, what to eat, which beach to swim at, or which scooter rental company to use.
"""

FURTHER_READING = Path("C:/tmp/further_reading.md").read_text(encoding="utf-8")

# Insert preface before first chapter, then append back matter
CHAPTER_HEADING_RE = re.compile(r"^# Chapter 1:", re.MULTILINE)
m = CHAPTER_HEADING_RE.search(text)
prefix = text[: m.start()]
body = text[m.start():]
new_text = (
    prefix + PREFACE + body
    + "\n\n---\n\n" + READING_GUIDE
    + "\n\n---\n\n" + GLOSSARY
    + "\n\n---\n\n" + SOURCES
    + "\n\n---\n\n" + FURTHER_READING
)
MD.write_text(new_text, encoding="utf-8")
print(f"manuscript.md: {len(new_text):,} bytes")

# 6. Merge React + swap payload/manuscript + inject all CSS
v1_text = V1.read_text(encoding="utf-8")
v3_html = HTML.read_text(encoding="utf-8")

PAYLOAD_RE = re.compile(
    r'(<script id="book-payload" type="application/json">)(.*?)(</script>)',
    re.DOTALL,
)
MANUSCRIPT_RE = re.compile(
    r'(<script id="book-manuscript" type="text/markdown">)(.*?)(</script>)',
    re.DOTALL,
)
m_pay = PAYLOAD_RE.search(v3_html)
new_payload_body = m_pay.group(2)

merged = PAYLOAD_RE.sub(lambda mm: mm.group(1) + new_payload_body + mm.group(3),
                        v1_text, count=1)
merged = MANUSCRIPT_RE.sub(lambda mm: mm.group(1) + new_text + mm.group(3),
                            merged, count=1)

# Markdown-table CSS (from v4.2)
TABLE_CSS = """
<style id="md-table-theme">
.markdown-content table, article table, main table, table {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 0.92em;
  border-collapse: collapse;
  margin: 1em auto;
  max-width: 100%;
  font-variant-numeric: tabular-nums;
}
.markdown-content table thead th, article table thead th, main table thead th, table thead th {
  border-top: 1.2px solid #444;
  border-bottom: 1px solid #444;
  background: #F1ECDC;
  font-weight: bold;
  padding: 6px 10px;
  text-align: left;
  font-size: 0.95em;
}
.markdown-content table tbody td, article table tbody td, main table tbody td, table tbody td {
  border-top: 0.4px solid #e3e3e3;
  padding: 5px 10px;
}
.markdown-content table tbody tr:last-child td, article table tbody tr:last-child td,
main table tbody tr:last-child td, table tbody tr:last-child td {
  border-bottom: 1.2px solid #444;
}
.hero-table .gt_table { margin: 0 auto; max-width: 100%; }
.hero-table { margin: 1.2em 0; }
@media print {
  .hero-table, table { page-break-inside: avoid; break-inside: avoid; }
}
</style>
"""

# Prose-furniture CSS (new in v4.3)
FURNITURE_CSS = Path("C:/tmp/v4_3_css.html").read_text(encoding="utf-8")

merged = merged.replace("</head>", TABLE_CSS + "\n" + FURNITURE_CSS + "\n</head>", 1)

HTML.write_text(merged, encoding="utf-8")
print(f"manuscript.html: {len(merged):,} bytes")

# 7. Render PDF
print_pdf(HTML, REL / "manuscript.pdf")
pdf_size = (REL / "manuscript.pdf").stat().st_size
print(f"manuscript.pdf: {pdf_size:,} bytes")

from pypdf import PdfReader
pages = len(PdfReader(str(REL / "manuscript.pdf")).pages)
print(f"pages = {pages}")
