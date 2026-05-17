from pathlib import Path
from types import SimpleNamespace
from scripts.synthesize.topic_map import build_topic_map

def _bk(monkeypatch, concepts, claims):
    """Patch the sibling_skills loader to return a fake book-knowledge module."""
    import scripts.synthesize.topic_map as tm
    fake_bk = SimpleNamespace(
        list_concepts=lambda root: concepts,
        query_claims=lambda filter_, root: claims,
    )
    monkeypatch.setattr(tm, "_load_book_knowledge", lambda: fake_bk)

def _bt(monkeypatch, tree):
    import scripts.synthesize.topic_map as tm
    fake_bt = SimpleNamespace(read_thesis_tree=lambda chap, root: tree)
    monkeypatch.setattr(tm, "_load_book_thesis", lambda: fake_bt)

def test_topic_map_writes_concept_rows(tmp_path, monkeypatch):
    concepts = [
        SimpleNamespace(slug="finality", title="Finality", sources=["s1"], surface_forms=["finality"]),
        SimpleNamespace(slug="longest-chain", title="Longest chain", sources=["s2"], surface_forms=["lc"]),
    ]
    claims = [
        SimpleNamespace(id="cl1", state="verified", tags=["finality"], source_id="s1", body="...", locator="p.1"),
        SimpleNamespace(id="cl2", state="verified", tags=["finality"], source_id="s1", body="...", locator="p.2"),
        SimpleNamespace(id="cl3", state="verified", tags=["longest-chain"], source_id="s2", body="...", locator="p.3"),
    ]
    tree = SimpleNamespace(chapter_id="ch-01", nodes=[
        SimpleNamespace(node_id="n1", statement="...", tags=["finality"], required_evidence_kind="empirical", parent_id=None),
        SimpleNamespace(node_id="n2", statement="...", tags=["longest-chain"], required_evidence_kind="empirical", parent_id=None),
    ])
    _bk(monkeypatch, concepts, claims)
    _bt(monkeypatch, tree)
    build_topic_map(tmp_path, chapter_id="ch-01")
    body = (tmp_path / "syntopical" / "topic-map.md").read_text(encoding="utf-8")
    # Both concepts appear with their per-concept verified-claim counts
    assert "finality" in body
    assert "longest-chain" in body
    # The count for finality should be 2 (two verified claims tagged finality)
    assert "n_verified_claims=2" in body or "| 2 |" in body
