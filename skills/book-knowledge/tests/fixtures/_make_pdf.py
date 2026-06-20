"""Generate a deterministic synthetic PDF for tests. Run once."""
from pathlib import Path
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas


def build(out_path: Path) -> None:
    c = canvas.Canvas(str(out_path), pagesize=LETTER)
    pages = [
        ("Chapter 1: Architecture",
         "The system has three components.",
         "The orchestrator routes events."),
        ("Chapter 2: Validation",
         "SHACL validates RDF datasets.",
         "Conformance reports list violations."),
        ("Chapter 3: Provenance",
         "PROV-O models entities, activities, and agents.",
         "wasDerivedFrom links generated entities to sources."),
    ]
    for title, line2, line3 in pages:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(72, 720, title)
        c.setFont("Helvetica", 11)
        c.drawString(72, 690, line2)
        c.drawString(72, 670, line3)
        c.showPage()
    c.save()


def build_kerned(out_path: Path) -> None:
    """A tightly-kerned page: words sit a hair too close for pdfplumber's
    default word tolerance, so extract_text() merges them into one run with no
    inter-word spaces. extract_words(x_tolerance=1) still splits on the narrow
    gaps and recovers the spacing — the exact PDF that verify_claim's word-box
    fallback variant exists to handle."""
    sentence = "stakeholders have the ability to revoke their delegative appointment"
    c = canvas.Canvas(str(out_path), pagesize=LETTER)
    c.setFont("Helvetica", 11)
    x = 72.0
    for word in sentence.split():
        c.drawString(x, 700, word)
        x += c.stringWidth(word, "Helvetica", 11) + 2.0
    c.showPage()
    c.save()


if __name__ == "__main__":
    build(Path(__file__).parent / "small.pdf")
    build_kerned(Path(__file__).parent / "kerned.pdf")
