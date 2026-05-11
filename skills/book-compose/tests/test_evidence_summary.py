from datetime import datetime, timezone
from pathlib import Path
import shutil

from scripts.evidence_summary import build_evidence_summary
from scripts.sibling_skills import book_knowledge_root, load_book_knowledge_module


def _seed(tmp_path: Path) -> Path:
    workspace_mod = load_book_knowledge_module("workspace")
    ledger_mod = load_book_knowledge_module("ledger")
    bk = book_knowledge_root()
    workspace = workspace_mod.init_workspace(tmp_path / "book")
    layout = workspace_mod.WorkspaceLayout(workspace)
    shutil.copy(bk / "assets" / "shapes.ttl", layout.shapes)
    for i in range(2):
        ledger_mod.append_claim(layout, {
            "claim_id": f"clm-2026-00000{i+1}",
            "canonical_text": f"claim {i}",
            "status": "verified",
            "claim_type": "fact",
            "confidence": 0.9 + i * 0.01,
            "source_spans": [{"doc_id": "small", "page_index": i+1, "locator_text": "abcd"}],
            "supports_chapters": ["ch-03"],
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
    return workspace


def test_evidence_summary_lists_each_claim(tmp_path):
    workspace = _seed(tmp_path)
    summary = build_evidence_summary(workspace, "ch-03")
    assert "clm-2026-000001" in summary
    assert "clm-2026-000002" in summary
    assert "small" in summary
    assert "page" in summary.lower()


def test_evidence_summary_for_empty_chapter(tmp_path):
    workspace = _seed(tmp_path)
    summary = build_evidence_summary(workspace, "ch-99")
    assert "no verified claims" in summary.lower() or "(none)" in summary
