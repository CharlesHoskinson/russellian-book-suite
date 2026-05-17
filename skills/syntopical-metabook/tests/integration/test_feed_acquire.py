from pathlib import Path
from types import SimpleNamespace
from scripts.gap.coverage_report import build_coverage_report
from scripts.gap.feed_acquire import seed_from_gap_report
from scripts.acquire.manifest import read_pending_seeds

def test_uncovered_statements_appended_to_pending_seeds(tmp_path, monkeypatch):
    chap = tmp_path / "chapters" / "ch-01"
    chap.mkdir(parents=True)
    (chap / "thesis-tree.yaml").write_text(
        "chapter_id: ch-01\nnodes:\n"
        "  - node_id: n1\n    statement: Finality is irreversible.\n"
        "    tags: [finality]\n    required_evidence_kind: empirical\n    parent_id: null\n"
        "  - node_id: n2\n    statement: Validators are honest.\n"
        "    tags: [trust]\n    required_evidence_kind: empirical\n    parent_id: null\n",
        encoding="utf-8")
    import scripts.gap.coverage_report as gr
    fake_bk = SimpleNamespace(query_claims=lambda f, root: [])  # no claims → both nodes uncovered
    monkeypatch.setattr(gr, "_load_book_knowledge", lambda: fake_bk)
    import yaml as _yaml
    def _read_tree(chap_id, root):
        raw = _yaml.safe_load((root / "chapters" / chap_id / "thesis-tree.yaml").read_text(encoding="utf-8"))
        return SimpleNamespace(chapter_id=raw["chapter_id"], nodes=[SimpleNamespace(**n) for n in raw["nodes"]])
    monkeypatch.setattr(gr, "_load_book_thesis", lambda: SimpleNamespace(read_thesis_tree=_read_tree))
    report = build_coverage_report(tmp_path, chapter_id="ch-01", required_per_node=3)
    seed_from_gap_report(tmp_path, chapter_id="ch-01")
    seeds = read_pending_seeds(tmp_path / "syntopical" / "acquisition" / "pending-seeds.txt")
    assert "Finality is irreversible." in seeds
    assert "Validators are honest." in seeds
