import json
from pathlib import Path
from scripts.adapters.openalex import _parse_work, OpenAlexWork, PaperRef

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "openalex_arxiv.json"

def test_parse_work_returns_dataclass():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    w = _parse_work(data)
    assert isinstance(w, OpenAlexWork)
    assert w.openalex_id.startswith("https://openalex.org/W")
    assert w.title
    assert w.doi
    assert isinstance(w.references, list)

def test_parse_paper_ref_handles_partial():
    ref = {"id": "https://openalex.org/W123", "title": "Foo", "publication_year": 2022,
           "cited_by_count": 5, "doi": "https://doi.org/10.x/y"}
    p = PaperRef.from_openalex(ref)
    assert p.openalex_id == "https://openalex.org/W123"
    assert p.year == 2022
    assert p.citation_count == 5
    assert p.external_ids.get("doi") == "10.x/y"
