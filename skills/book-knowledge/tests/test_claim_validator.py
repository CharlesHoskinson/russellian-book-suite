from datetime import datetime, timezone

import pytest
from scripts.claim_validator import validate_claim, ClaimValidationError


def _good_claim(**overrides) -> dict:
    base = {
        "claim_id": "clm-2026-000001",
        "canonical_text": "SHACL conformance reports list violations.",
        "status": "proposed",
        "claim_type": "fact",
        "confidence": 0.9,
        "source_spans": [
            {"doc_id": "small", "page_index": 2, "locator_text": "SHACL validates RDF datasets."}
        ],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    base.update(overrides)
    return base


def test_valid_claim_passes():
    validate_claim(_good_claim())


def test_invalid_claim_id_pattern_fails():
    with pytest.raises(ClaimValidationError):
        validate_claim(_good_claim(claim_id="claim-1"))


def test_status_must_be_in_state_machine():
    with pytest.raises(ClaimValidationError):
        validate_claim(_good_claim(status="approved"))


def test_confidence_must_be_in_unit_interval():
    with pytest.raises(ClaimValidationError):
        validate_claim(_good_claim(confidence=1.5))
    with pytest.raises(ClaimValidationError):
        validate_claim(_good_claim(confidence=-0.1))


def test_source_spans_must_be_non_empty():
    with pytest.raises(ClaimValidationError):
        validate_claim(_good_claim(source_spans=[]))


def test_extra_properties_rejected():
    bad = _good_claim()
    bad["extra"] = 1
    with pytest.raises(ClaimValidationError):
        validate_claim(bad)
