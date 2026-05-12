from datetime import datetime, timezone

import pytest
from scripts.claim_validator import (
    validate_claim, assert_transition_allowed, ClaimValidationError,
)


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


def test_refuted_status_accepted():
    rec = _good_claim(status="refuted")
    validate_claim(rec)


def test_p_prior_and_p_posterior_accepted():
    rec = _good_claim(p_prior=0.7, p_posterior=0.82)
    validate_claim(rec)


def test_load_bearing_accepted():
    rec = _good_claim(load_bearing=True)
    validate_claim(rec)


def test_counter_claim_ids_accepted():
    rec = _good_claim(counter_claim_ids=["cc-0001-abcdef", "cc-0001-fedcba"])
    validate_claim(rec)


def test_p_posterior_out_of_range_rejected():
    rec = _good_claim(p_posterior=1.5)
    with pytest.raises(ClaimValidationError):
        validate_claim(rec)


def test_disputed_to_refuted_allowed():
    assert_transition_allowed("disputed", "refuted")


def test_verified_to_refuted_rejected():
    with pytest.raises(ClaimValidationError):
        assert_transition_allowed("verified", "refuted")


def test_refuted_is_terminal():
    with pytest.raises(ClaimValidationError):
        assert_transition_allowed("refuted", "verified")
    with pytest.raises(ClaimValidationError):
        assert_transition_allowed("refuted", "disputed")
