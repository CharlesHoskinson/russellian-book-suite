import pytest

pytestmark = pytest.mark.windows_canary

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


def test_query_chapter_evidence_reads_ledger_not_trig(tmp_path):
    """P5.1 cutover: evidence comes from the Cozo projection of the claim LEDGER,
    not from the TriG dataset. Seed the ledger, then DELETE the TriG entirely — the
    old rdflib/SPARQL path would return [] with no dataset; the Cozo path must still
    find the 3 verified claims from the ledger."""
    workspace_mod = load_book_knowledge_module("workspace")
    ledger_mod = load_book_knowledge_module("ledger")
    workspace = workspace_mod.init_workspace(tmp_path / "book")
    layout = workspace_mod.WorkspaceLayout(workspace)
    for i in range(3):
        ledger_mod.append_claim(layout, {
            "claim_id": f"clm-2026-00000{i+1}",
            "canonical_text": f"claim text {i}",
            "status": "verified",
            "claim_type": "fact",
            "confidence": 0.9,
            "source_spans": [{"doc_id": "small", "locator_text": "abcd"}],
            "supports_chapters": ["ch-07"],
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
    if layout.dataset.exists():
        layout.dataset.unlink()  # remove the TriG so only the ledger remains
    result = query_chapter_evidence(workspace, "ch-07")
    assert sorted(result["claims"]) == ["clm-2026-000001", "clm-2026-000002", "clm-2026-000003"]


def test_query_chapter_evidence_matches_escape_needing_chapter_id(tmp_path):
    """The query must mint the chapter URI the SAME way the projector does
    (urllib quote), so a chapter id needing escaping (here, a space) still joins —
    the projector stores .../chapters/ch%2003, so a raw .../chapters/ch 03 lookup
    would miss it (audit IMPORTANT). Also guards the EDN literal against a stray
    quote in the id."""
    workspace = _seed(tmp_path, "ch 03")
    result = query_chapter_evidence(workspace, "ch 03")
    assert len(result["claims"]) == 3
