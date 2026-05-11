"""JSON Schema validation and supersession rules for claim records."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SCHEMA = json.loads((ASSETS / "claim-record.schema.json").read_text(encoding="utf-8"))

VALID_TRANSITIONS = {
    "proposed": {"verified", "disputed", "superseded"},
    "verified": {"disputed", "superseded"},
    "disputed": {"verified", "superseded"},
    "superseded": set(),
}


class ClaimValidationError(Exception):
    pass


def validate_claim(record: dict) -> None:
    try:
        jsonschema.validate(record, SCHEMA)
    except jsonschema.ValidationError as e:
        raise ClaimValidationError(str(e)) from e


def assert_transition_allowed(old_status: str, new_status: str) -> None:
    allowed = VALID_TRANSITIONS.get(old_status, set())
    if new_status not in allowed:
        raise ClaimValidationError(
            f"transition {old_status!r} -> {new_status!r} not allowed; "
            f"valid: {sorted(allowed) or 'none (terminal)'}"
        )
