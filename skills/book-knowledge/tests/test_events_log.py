import pytest
from scripts.workspace import init_workspace
from scripts.events_log import append_event, read_events, EventError


def test_append_event(tmp_path):
    init_workspace(tmp_path)
    append_event(tmp_path, {
        "timestamp": "2026-05-11T00:00:00Z",
        "claim_id": "clm-2026-000001",
        "from": "verified", "to": "disputed",
        "cause_ticket_id": "ch07-D11-04",
        "cause_class": "unsupported_claim",
        "operator": "charles@host",
    })
    events = read_events(tmp_path)
    assert events[0]["to"] == "disputed"


def test_invalid_state_rejected(tmp_path):
    init_workspace(tmp_path)
    with pytest.raises(EventError):
        append_event(tmp_path, {
            "timestamp": "2026-05-11T00:00:00Z",
            "claim_id": "clm-2026-000001",
            "from": "verified", "to": "not-a-state",
            "cause_ticket_id": "x", "cause_class": "y", "operator": "z",
        })


def test_invalid_claim_id_rejected(tmp_path):
    init_workspace(tmp_path)
    with pytest.raises(EventError):
        append_event(tmp_path, {
            "timestamp": "2026-05-11T00:00:00Z",
            "claim_id": "bad-id",
            "from": "verified", "to": "disputed",
            "cause_ticket_id": "x", "cause_class": "y", "operator": "z",
        })
