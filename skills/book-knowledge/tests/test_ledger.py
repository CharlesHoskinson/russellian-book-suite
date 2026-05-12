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


def test_transition_status_writes_event(tmp_path):
    from scripts.events_log import read_events
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    base = {
        "claim_id": "clm-2026-000001",
        "canonical_text": "Hi text.",
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.7,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "created_at": "2026-05-11T00:00:00Z",
    }
    append_claim(layout, base)
    transition_status(layout, "clm-2026-000001", "disputed",
                      cause_ticket_id="ch07-D11-04",
                      cause_class="unsupported_claim",
                      operator="charles@host")
    events = read_events(tmp_path / "book")
    assert events[0]["from"] == "verified"
    assert events[0]["to"] == "disputed"
    assert events[0]["cause_ticket_id"] == "ch07-D11-04"


def test_transition_status_resets_p_prior(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    base = {
        "claim_id": "clm-2026-000001",
        "canonical_text": "Hi text.",
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.7,
        "p_prior": 0.7,
        "p_posterior": 0.85,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "created_at": "2026-05-11T00:00:00Z",
    }
    append_claim(layout, base)
    transition_status(layout, "clm-2026-000001", "disputed",
                      cause_ticket_id="x", cause_class="x", operator="x")
    records = read_claims(layout)
    latest = [r for r in records if r["claim_id"] == "clm-2026-000001"][-1]
    assert latest["status"] == "disputed"
    assert latest["p_prior"] == 0.2  # prior_for_status("disputed")
