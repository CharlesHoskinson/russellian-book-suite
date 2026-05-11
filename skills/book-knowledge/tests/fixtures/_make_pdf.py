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


if __name__ == "__main__":
    build(Path(__file__).parent / "small.pdf")
