"""JSON Schema validation and supersession rules for claim records.

REQ-KG-009 / REQ-KG-009b / REQ-KG-020: the claim status vocabulary -- the 5
states AND the allowed transition matrix -- is authored in ONE place,
``assets/status-enum.edn``. ``VALID_STATES`` and ``VALID_TRANSITIONS`` are
DERIVED from that source at import; the matrix cannot name a status absent from
``:states``. Edit the vocabulary in the EDN file, never here.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import edn_format
import jsonschema

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SCHEMA = json.loads((ASSETS / "claim-record.schema.json").read_text(encoding="utf-8"))


class ClaimValidationError(Exception):
    pass


class ClaimVocabularyError(Exception):
    """Raised when the status vocabulary EDN is missing/malformed or names an out-of-source status."""
    pass


# NOTE: an identical helper exists in cozo_store.py; consolidate into a shared edn util when a third consumer appears (rule of three).
def _kw_name(keyword: Any) -> str:
    """Return the bare name of an edn_format Keyword (no leading colon)."""
    return keyword.name


def _load_status_enum_text(text: str) -> tuple[list[str], dict[str, set[str]]]:
    """Parse the status-enum EDN text into ``(states, transitions)``.

    ``states`` is the authored list of status strings; ``transitions`` is
    ``{source_status: {target_status, ...}}`` derived from ``:transitions``.

    Enforces REQ-KG-020: every status appearing as a transition key OR target
    MUST be declared in ``:states``; otherwise a ``ClaimVocabularyError`` is
    raised. This is the pure helper the single-source tests exercise.

    A malformed EDN string or a missing ``:states``/``:transitions`` key also
    raises ``ClaimVocabularyError`` (a deploy-time config error, distinct from
    the per-claim ``ClaimValidationError``).
    """
    try:
        doc = edn_format.loads(text)
        raw_states = doc[edn_format.Keyword("states")]
        states = [_kw_name(s) for s in raw_states]

        raw_trans = doc[edn_format.Keyword("transitions")]
        items = raw_trans.dict.items() if hasattr(raw_trans, "dict") else raw_trans.items()
        transitions: dict[str, set[str]] = {
            _kw_name(src): {_kw_name(t) for t in targets} for src, targets in items
        }
    except ClaimVocabularyError:
        raise
    except (KeyError, AttributeError, TypeError, edn_format.EDNDecodeError) as e:
        raise ClaimVocabularyError(
            f"status vocabulary EDN is missing/malformed: {e!r}; expected a map "
            "with :states (list of keywords) and :transitions (map of keyword -> "
            "set of keywords)"
        ) from e

    declared = set(states)
    named = set(transitions)
    for targets in transitions.values():
        named |= targets
    stray = named - declared
    if stray:
        raise ClaimVocabularyError(
            f"status(es) {sorted(stray)!r} named in :transitions are absent "
            f"from :states {states!r}; the transition matrix may not reference "
            "an out-of-source status (REQ-KG-020)"
        )
    return states, transitions


def _load_status_enum(path: Path) -> tuple[list[str], dict[str, set[str]]]:
    """Read and parse the status-enum EDN at ``path``."""
    return _load_status_enum_text(path.read_text(encoding="utf-8"))


_STATES, VALID_TRANSITIONS = _load_status_enum(ASSETS / "status-enum.edn")
VALID_STATES: frozenset[str] = frozenset(_STATES)


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
