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


def map_remedy_proposal_to_transition(proposal: dict) -> dict | None:
    """Normalise a BookLogic remedy proposal into the propose_writeback dict shape.

    REQ-QA-PIPE-011: proposed transitions carry :cause-remedy-id.
    REQ-QA-PIPE-012: :requires :human-review threads through as auto_apply=False.

    The remedy proposal already carries :transition with kind/claim_id/to;
    this function only renames keys to match the rest of the pipeline and
    threads :requires / :auto_apply through.
    """
    t = proposal.get("transition")
    if not isinstance(t, dict):
        return None
    if t.get("kind") != "claim":
        return None
    return {
        "kind":            "claim",
        "claim_id":        t["claim_id"],
        "to":              t["to"],
        # Remedy proposals have no `from`; apply_writeback decides based on current status.
        "cause_ticket_id": proposal["remedy_id"],
        "cause_class":     "booklogic_remedy",
        "requires":        proposal["requires"],
        "auto_apply":      proposal["auto_apply"],
    }
