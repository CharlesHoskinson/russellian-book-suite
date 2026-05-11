from datetime import datetime, timezone
from pathlib import Path

import pytest
from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.ledger import (
    next_claim_id, append_claim, read_claims, transition_status,
    LedgerError,
)


def _stub_claim(claim_id="clm-2026-000001", status="proposed") -> dict:
    return {
        "claim_id": claim_id,
        "canonical_text": "Atomic propositions are independently verifiable.",
        "status": status,
        "claim_type": "fact",
        "confidence": 0.85,
        "source_spans": [{"doc_id": "small", "page_index": 1, "locator_text": "three components"}],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def test_next_claim_id_starts_at_one(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    cid = next_claim_id(layout)
    assert cid.endswith("-000001")


def test_next_claim_id_increments(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    cid1 = next_claim_id(layout)
    append_claim(layout, _stub_claim(claim_id=cid1))
    cid2 = next_claim_id(layout)
    assert cid1 != cid2
    assert cid2.endswith("-000002")


def test_read_claims_returns_appended(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    append_claim(layout, _stub_claim())
    claims = read_claims(layout)
    assert len(claims) == 1
    assert claims[0]["status"] == "proposed"


def test_transition_status_writes_new_record(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    append_claim(layout, _stub_claim())
    transition_status(layout, "clm-2026-000001", "verified", note="test")
    claims = read_claims(layout)
    statuses = [c["status"] for c in claims if c["claim_id"] == "clm-2026-000001"]
    assert "verified" in statuses


def test_transition_to_invalid_state_raises(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    append_claim(layout, _stub_claim(status="superseded"))
    with pytest.raises(LedgerError):
        transition_status(layout, "clm-2026-000001", "verified")


def test_append_validates_record(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    bad = _stub_claim()
    bad["status"] = "approved"
    with pytest.raises(LedgerError):
        append_claim(layout, bad)
