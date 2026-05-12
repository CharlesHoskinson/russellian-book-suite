"""Pure mapping from QA defect ticket → proposed ledger transition."""


def map_ticket_to_proposed_transition(ticket: dict) -> dict | None:
    cls = ticket.get("class")
    if cls == "unsupported_claim":
        if ticket.get("claim_current_status") != "verified":
            return None
        return {"kind": "claim", "claim_id": ticket["claim_id"],
                "from": "verified", "to": "disputed",
                "cause_ticket_id": ticket["id"], "cause_class": cls}
    if cls == "refuted_by_new_source":
        if ticket.get("claim_current_status") != "disputed":
            return None
        return {"kind": "claim", "claim_id": ticket["claim_id"],
                "from": "disputed", "to": "refuted",
                "cause_ticket_id": ticket["id"], "cause_class": cls}
    if cls == "addressed_rival":
        return {"kind": "counter_claim",
                "counter_claim_id": ticket["counter_claim_id"],
                "new_status": "addressed",
                "chapter_id": ticket.get("chapter_id"),
                "cause_ticket_id": ticket["id"], "cause_class": cls}
    return None
