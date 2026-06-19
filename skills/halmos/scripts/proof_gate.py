"""Math/science prose gating for proof obligations."""
from __future__ import annotations


def render_math_science_claim(claim: dict, obligation: dict | None) -> dict:
    """Render a claim only when its proof obligation permits the assertion."""
    text = claim.get("canonical_text", "")
    status = (obligation or {}).get("status")

    if status == "discharged" or obligation is None:
        return {
            "claim_id": claim.get("claim_id"),
            "asserted_verified": True,
            "mode": "verified",
            "sentence": text,
        }

    if status == "waived":
        reason = obligation.get("waiver_reason", "waiver recorded")
        return {
            "claim_id": claim.get("claim_id"),
            "asserted_verified": False,
            "mode": "conjectural",
            "sentence": f"Conjectural: {text} (proof obligation waived: {reason}).",
        }

    return {
        "claim_id": claim.get("claim_id"),
        "asserted_verified": False,
        "mode": "omitted",
        "sentence": "",
    }
