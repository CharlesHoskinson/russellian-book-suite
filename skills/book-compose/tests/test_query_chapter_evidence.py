from datetime import datetime, timezone
from pathlib import Path
import shutil

from scripts.query_chapter_evidence import query_chapter_evidence
from scripts.sibling_skills import book_knowledge_root, load_book_knowledge_module


def _seed(tmp_path: Path, chapter: str) -> Path:
    workspace_mod = load_book_knowledge_module("workspace")
    ledger_mod = load_book_knowledge_module("ledger")
    project_graph_mod = load_book_knowledge_module("project_graph")

    bk = book_knowledge_root()
    workspace = workspace_mod.init_workspace(tmp_path / "book")
    layout = workspace_mod.WorkspaceLayout(workspace)
    shutil.copy(bk / "assets" / "shapes.ttl", layout.shapes)
    for i in range(3):
        ledger_mod.append_claim(layout, {
            "claim_id": f"clm-2026-00000{i+1}",
            "canonical_text": f"claim text {i}",
            "status": "verified",
            "claim_type": "fact",
            "confidence": 0.9,
            "source_spans": [{"doc_id": "small", "locator_text": "abcd"}],
            "supports_chapters": [chapter],
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
    project_graph_mod.project_graph(layout)
    return workspace


def test_query_chapter_evidence_returns_assigned_claims(tmp_path):
    workspace = _seed(tmp_path, "ch-03")
    result = query_chapter_evidence(workspace, "ch-03")
    assert result["chapter_id"] == "ch-03"
    assert len(result["claims"]) == 3
    assert all(c.startswith("clm-") for c in result["claims"])


def test_query_chapter_evidence_returns_empty_for_unknown_chapter(tmp_path):
    workspace = _seed(tmp_path, "ch-03")
    result = query_chapter_evidence(workspace, "ch-99")
    assert result["claims"] == []
