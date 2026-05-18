from pathlib import Path
import yaml
from scripts.lens.project_lens import project_lens

def _seed_synthesize_files(ws: Path):
    """Build a fixture syntopical/ tree the lens reads from."""
    syn = ws / "syntopical"
    (syn / "disputed-questions").mkdir(parents=True)
    (syn / "concepts").mkdir(parents=True)
    (syn / "reports").mkdir(parents=True)
    (syn / "topic-map.md").write_text(
        "# Topic Map\n\n## n1\n\n| slug | sources | n_verified_claims |\n"
        "|---|---|---|\n| finality | s1 | 2 |\n| unrelated | s9 | 1 |\n\n",
        encoding="utf-8")
    (syn / "disputed-questions" / "finality.md").write_text(
        "# Disputed Questions: finality\n\n"
        "| Question | Position | Source | Claim-ID | Rewrite-witness | Evidence locator |\n"
        "|---|---|---|---|---|---|\n"
        "| q | yes | s1 | cl1 | rule-1 | p.1 |\n", encoding="utf-8")
    (syn / "concepts" / "nakamoto-consensus.md").write_text(
        "# Canonical Concept: nakamoto-consensus\n\n"
        "| Alternate slug | Surface form | Source | Rewrite-witness |\n"
        "|---|---|---|---|\n"
        "| longest-chain | longest-chain rule | s1 | rule-unify-1 |\n", encoding="utf-8")

def test_project_lens_writes_lens_file(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir()
    chap = ws / "chapters" / "ch-01"
    chap.mkdir(parents=True)
    (chap / "contract.yaml").write_text(
        "id: ch-01\ntitle: Finality\nsummary: A chapter on finality.\n"
        "tags: [finality]\n", encoding="utf-8")
    (chap / "thesis-tree.yaml").write_text(
        "chapter_id: ch-01\nnodes:\n  - node_id: n1\n    statement: x\n    tags: [finality]\n"
        "    required_evidence_kind: empirical\n    parent_id: null\n",
        encoding="utf-8")
    _seed_synthesize_files(ws)
    out_path = project_lens(workspace_root=ws, chapter_id="ch-01", source_run_id="run-1")
    assert out_path == ws / "syntopical" / "lenses" / "ch-01.md"
    body = out_path.read_text(encoding="utf-8")
    # Frontmatter
    assert body.startswith("---")
    fm_end = body.index("\n---\n", 4)
    fm = yaml.safe_load(body[3:fm_end])
    assert fm["chapter_id"] == "ch-01"
    assert fm["source_run_id"] == "run-1"
    assert "n_topics" in fm and "n_disputed" in fm and "n_concepts" in fm
    assert "coverage_score" in fm
    # Required section order
    def idx(s):
        return body.index(s)
    assert idx("## Topics") < idx("## Disputed Questions") < idx("## Concept Reconciliation") < idx("## Coverage")
    # Tag-filtered: finality content appears, unrelated does NOT appear in topics
    assert "finality" in body
    assert "unrelated" not in body
