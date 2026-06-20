"""Writer gating tests for proof-obligation consumption (REQ-PROOF-005..006)."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

from scripts.proof_gate import render_math_science_claim


def _claim() -> dict:
    return {
        "claim_id": "clm-2026-000001",
        "canonical_text": "Every finite Boolean algebra has an atom.",
        "status": "verified",
    }


def test_undischarged_claim_not_asserted() -> None:
    """REQ-PROOF-005: pending obligations are not asserted as verified."""
    rendered = render_math_science_claim(
        _claim(),
        {
            "id": "obl-clm-2026-000001",
            "linked_claim": "clm-2026-000001",
            "status": "pending",
            "checker_kind": "lean",
        },
    )

    assert rendered["asserted_verified"] is False
    assert rendered["mode"] in {"omitted", "non-canonical"}
    assert "verified" not in rendered["sentence"].lower()


def test_waived_claim_stated_conjectural() -> None:
    """REQ-PROOF-006: waived obligations are conjectural with the waiver noted."""
    rendered = render_math_science_claim(
        _claim(),
        {
            "id": "obl-clm-2026-000001",
            "linked_claim": "clm-2026-000001",
            "status": "waived",
            "checker_kind": "lean",
            "waiver_reason": "out of formal scope for this edition",
        },
    )

    sentence = rendered["sentence"].lower()
    assert rendered["asserted_verified"] is False
    assert rendered["mode"] == "conjectural"
    assert "conjectural" in sentence
    assert "waived" in sentence
    assert "out of formal scope for this edition" in sentence
