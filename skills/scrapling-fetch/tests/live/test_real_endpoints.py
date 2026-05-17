"""Live tests against real upstreams. Run via `pytest -m live`. Not in default CI."""
import pytest

@pytest.mark.live
def test_arxiv_get_real():
    from scripts.adapters.arxiv import get
    p = get("2310.04673")
    assert p.title
    assert len(p.authors) > 0
    assert p.abstract

@pytest.mark.live
def test_openalex_work_real():
    from scripts.adapters.openalex import work
    w = work("10.48550/arXiv.2310.04673")
    assert w.title

@pytest.mark.live
def test_doi_resolve_real():
    from scripts.adapters.doi import resolve
    r = resolve("10.48550/arXiv.2310.04673")
    assert r.final_url.startswith("https://")

# Semantic Scholar live test omitted — it sometimes blocks even StealthySession
# and would make this suite flaky. Add it when a robust adapter pattern is established.
