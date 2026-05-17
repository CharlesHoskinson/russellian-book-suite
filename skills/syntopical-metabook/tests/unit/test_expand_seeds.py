from dataclasses import dataclass
from scripts.acquire.expand_seeds import expand_seeds, PaperRef

def test_dedup_by_arxiv_id(monkeypatch):
    a = PaperRef(title="A", arxiv_id="2310.04673", doi=None, ss_id=None, openalex_id=None,
                 year=2023, citation_count=10, external_ids={})
    b = PaperRef(title="A (dup)", arxiv_id="2310.04673", doi=None, ss_id=None, openalex_id=None,
                 year=2023, citation_count=10, external_ids={})
    monkeypatch.setattr("scripts.acquire.expand_seeds._fetch_neighbors",
                        lambda seed, depth: [a, b])
    out = expand_seeds(seeds=["arxiv:2310.04673"], depth=1)
    assert len(out) == 1

def test_dedup_falls_through_to_doi_then_openalex(monkeypatch):
    a = PaperRef(title="A", arxiv_id=None, doi="10.x/y", ss_id=None, openalex_id=None,
                 year=2023, citation_count=10, external_ids={})
    b = PaperRef(title="A dup", arxiv_id=None, doi="10.x/y", ss_id=None, openalex_id=None,
                 year=2023, citation_count=10, external_ids={})
    monkeypatch.setattr("scripts.acquire.expand_seeds._fetch_neighbors",
                        lambda seed, depth: [a, b])
    out = expand_seeds(seeds=["10.x/y"], depth=1)
    assert len(out) == 1

def test_multiple_seeds_union(monkeypatch):
    a = PaperRef(title="A", arxiv_id="1", doi=None, ss_id=None, openalex_id=None,
                 year=2023, citation_count=10, external_ids={})
    b = PaperRef(title="B", arxiv_id="2", doi=None, ss_id=None, openalex_id=None,
                 year=2023, citation_count=10, external_ids={})
    monkeypatch.setattr("scripts.acquire.expand_seeds._fetch_neighbors",
                        lambda seed, depth: [a if seed == "s1" else b])
    out = expand_seeds(seeds=["s1", "s2"], depth=1)
    assert len(out) == 2
