"""Pure mapping from QA defect ticket → proposed ledger transition."""

# D11 (failed-entailment from lint_artifact/book-thesis) is semantically
# equivalent to unsupported_claim: a paragraph that does not entail its
# declared supports-node leaves the cited claim without manuscript backing.
D11_SYNONYMS: frozenset[str] = frozenset({"D11", "failed_entailment"})


def map_ticket_to_proposed_transition(ticket: dict) -> dict | None:
    cls = ticket.get("class")
    # Normalise D11 synonyms to "unsupported_claim" before dispatch.
    if cls in D11_SYNONYMS:
        cls = "unsupported_claim"
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
