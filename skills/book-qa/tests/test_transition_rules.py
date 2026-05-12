from scripts.transition_rules import map_ticket_to_proposed_transition


def _ticket(class_, **kw):
    return {"class": class_, "id": kw.pop("id", "tkt-1"), **kw}


def test_unsupported_claim_maps_to_disputed():
    t = _ticket("unsupported_claim", claim_id="clm-2026-000001",
                claim_current_status="verified")
    out = map_ticket_to_proposed_transition(t)
    assert out["from"] == "verified"
    assert out["to"] == "disputed"


def test_refuted_by_new_source_maps_to_refuted():
    t = _ticket("refuted_by_new_source", claim_id="clm-2026-000001",
                claim_current_status="disputed")
    out = map_ticket_to_proposed_transition(t)
    assert out["from"] == "disputed"
    assert out["to"] == "refuted"


def test_addressed_rival_returns_counter_claim_action():
    t = _ticket("addressed_rival", counter_claim_id="cc-2026-abcdef",
                chapter_id="ch07")
    out = map_ticket_to_proposed_transition(t)
    assert out["kind"] == "counter_claim"
    assert out["counter_claim_id"] == "cc-2026-abcdef"
    assert out["new_status"] == "addressed"


def test_unknown_class_returns_none():
    assert map_ticket_to_proposed_transition({"class": "unknown"}) is None


def test_unsupported_on_already_disputed_skips():
    t = _ticket("unsupported_claim", claim_id="clm-2026-000001",
                claim_current_status="disputed")
    assert map_ticket_to_proposed_transition(t) is None
