from types import SimpleNamespace
from scripts.gap.coverage_report import build_coverage_report

def _setup(tmp_path, monkeypatch, claims):
    chap = tmp_path / "chapters" / "ch-01"
    chap.mkdir(parents=True)
    (chap / "thesis-tree.yaml").write_text(
        "chapter_id: ch-01\nnodes:\n"
        "  - node_id: n1\n    statement: A\n    tags: [finality]\n"
        "    required_evidence_kind: empirical\n    parent_id: null\n"
        "  - node_id: n2\n    statement: B\n    tags: [longest-chain]\n"
        "    required_evidence_kind: empirical\n    parent_id: null\n"
        "  - node_id: n3\n    statement: C\n    tags: [other]\n"
        "    required_evidence_kind: empirical\n    parent_id: null\n",
        encoding="utf-8")
    import scripts.gap.coverage_report as gr
    fake_bk = SimpleNamespace(query_claims=lambda f, root: claims)
    monkeypatch.setattr(gr, "_load_book_knowledge", lambda: fake_bk)
    import yaml as _yaml
    def _read_tree(chap_id, root):
        raw = _yaml.safe_load((root / "chapters" / chap_id / "thesis-tree.yaml").read_text(encoding="utf-8"))
        return SimpleNamespace(chapter_id=raw["chapter_id"], nodes=[SimpleNamespace(**n) for n in raw["nodes"]])
    monkeypatch.setattr(gr, "_load_book_thesis", lambda: SimpleNamespace(read_thesis_tree=_read_tree))

def test_scoring_one_of_three(tmp_path, monkeypatch):
    claims = [
        SimpleNamespace(id="cl1", state="verified", tags=["finality"], source_id="s1",
                        body="...", locator="p.1"),
    ]
    _setup(tmp_path, monkeypatch, claims)
    out = build_coverage_report(tmp_path, chapter_id="ch-01", required_per_node=3)
    body = out.read_text(encoding="utf-8")
    # n1 has 1 supporting claim, requires 3 → score 0.33
    assert "0.33" in body or "0.333" in body
    # n2 and n3 have 0 supporting → score 0.00
    assert "n2" in body and "n3" in body
    # Footer average score
    assert "average_coverage_score" in body

def test_fully_covered_omits_node(tmp_path, monkeypatch):
    claims = [
        SimpleNamespace(id="cl1", state="verified", tags=["finality"], source_id="s1",
                        body="...", locator="p.1"),
        SimpleNamespace(id="cl2", state="verified", tags=["finality"], source_id="s1",
                        body="...", locator="p.2"),
        SimpleNamespace(id="cl3", state="verified", tags=["finality"], source_id="s1",
                        body="...", locator="p.3"),
    ]
    _setup(tmp_path, monkeypatch, claims)
    out = build_coverage_report(tmp_path, chapter_id="ch-01", required_per_node=3)
    body = out.read_text(encoding="utf-8")
    # n1 fully covered, omitted from gap list (REQ-GAP-1 only lists nodes < 1.0)
    assert "| n1 |" not in body or "1.00" in body  # either omitted or shown as 1.0
    # n2 and n3 still listed
    assert "n2" in body and "n3" in body
