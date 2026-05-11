from datetime import datetime, timezone
from pathlib import Path

import pytest
from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.ledger import append_claim
from scripts.ingest_markdown import ingest_markdown
from scripts.verify_claim import verify_claim, VerificationResult


def _claim_with_locator(locator: str, doc_id: str = "small") -> dict:
    return {
        "claim_id": "clm-2026-000001",
        "canonical_text": "placeholder claim text",
        "status": "proposed",
        "claim_type": "fact",
        "confidence": 0.8,
        "source_spans": [{"doc_id": doc_id, "locator_text": locator}],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def test_verify_passes_when_locator_text_present_in_source(tmp_path):
    workspace = init_workspace(tmp_path / "book")
    layout = WorkspaceLayout(workspace)
    ingest_markdown(Path("tests/fixtures/small.md"), workspace)
    append_claim(layout, _claim_with_locator("three components"))
    result = verify_claim(layout, "clm-2026-000001")
    assert result.ok is True
    assert result.new_status == "verified"


def test_verify_fails_when_locator_missing(tmp_path):
    workspace = init_workspace(tmp_path / "book")
    layout = WorkspaceLayout(workspace)
    ingest_markdown(Path("tests/fixtures/small.md"), workspace)
    append_claim(layout, _claim_with_locator("not in source"))
    result = verify_claim(layout, "clm-2026-000001")
    assert result.ok is False
    assert result.reason
    assert result.new_status == "proposed"


def test_verify_fails_for_unknown_doc_id(tmp_path):
    workspace = init_workspace(tmp_path / "book")
    layout = WorkspaceLayout(workspace)
    append_claim(layout, _claim_with_locator("anything", doc_id="missing"))
    with pytest.raises(FileNotFoundError):
        verify_claim(layout, "clm-2026-000001")
