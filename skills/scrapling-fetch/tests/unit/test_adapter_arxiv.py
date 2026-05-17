from pathlib import Path
from scripts.adapters.arxiv import _parse_abstract_page, ArxivPaper

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "arxiv_2310_04673.html"

def test_parse_abstract_page_returns_paper():
    html = FIXTURE.read_text(encoding="utf-8")
    p = _parse_abstract_page("2310.04673", html)
    assert isinstance(p, ArxivPaper)
    assert p.arxiv_id == "2310.04673"
    assert "LauraGPT" in p.title
    assert len(p.abstract) > 100
    assert p.pdf_url.endswith(".pdf")
    assert len(p.authors) > 0
