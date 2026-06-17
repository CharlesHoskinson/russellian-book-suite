"""Single-source-of-truth tests for the claim status vocabulary.

REQ-KG-009 / REQ-KG-009b / REQ-KG-020: ``assets/status-enum.edn`` is the one
authored source for the 5 claim states AND the allowed transition matrix.
``scripts.claim_validator`` derives ``VALID_TRANSITIONS`` and ``VALID_STATES``
from it at import; the matrix may not name a status absent from ``:states``.

Known, deliberately-NOT-asserted-absent remaining copies of the status list:
- ``assets/claim-record.schema.json`` -- JSON Schema cannot ``$ref`` an EDN
  file, so its ``status`` enum is an acknowledged derived copy. It is pinned to
  the single source by :func:`test_json_schema_matches_edn_source` below.
- ``assets/shapes.ttl`` -- its ``sh:in`` list is removed in P5, not here.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import edn_format
import pytest

from scripts import claim_validator

ASSETS = Path(claim_validator.__file__).resolve().parent.parent / "assets"
ENUM_EDN = ASSETS / "status-enum.edn"


def _edn_states_and_transitions() -> tuple[set[str], dict[str, set[str]]]:
    """Read the EDN source directly (independent of the validator's parse)."""
    doc = edn_format.loads(ENUM_EDN.read_text(encoding="utf-8"))
    states = {kw.name for kw in doc[edn_format.Keyword("states")]}
    raw = doc[edn_format.Keyword("transitions")]
    items = raw.dict.items() if hasattr(raw, "dict") else raw.items()
    transitions = {k.name: {t.name for t in v} for k, v in items}
    return states, transitions


def test_one_source_feeds_both():
    """REQ-KG-009: one EDN parse, two derived views (states + matrix)."""
    edn_states, edn_transitions = _edn_states_and_transitions()

    # View 1: the state set.
    assert set(claim_validator.VALID_STATES) == edn_states
    assert set(claim_validator.VALID_TRANSITIONS.keys()) == edn_states

    # View 2: the transition matrix.
    assert claim_validator.VALID_TRANSITIONS == edn_transitions


def test_no_second_enum_copy():
    """REQ-KG-009b: the matrix is derived, not re-typed, in claim_validator.py.

    Scoped to the Python source. The JSON-schema copy (drift-guarded by
    test_json_schema_matches_edn_source) and shapes.ttl ``sh:in`` (removed in P5)
    are the known remaining copies and are NOT asserted absent here.
    """
    src = Path(claim_validator.__file__).read_text(encoding="utf-8")

    # The old hard-coded dict literal style must be gone. Whitespace-agnostic:
    # catches any spacing of the old hard-coded VALID_TRANSITIONS dict literal.
    assert not re.search(r'"proposed"\s*:\s*\{', src), "old hard-coded VALID_TRANSITIONS dict literal still present"
    assert '"superseded": set()' not in src

    # VALID_TRANSITIONS must be built from the EDN load, not re-typed.
    assert "VALID_TRANSITIONS" in src
    assert "edn_format" in src
    assert "status-enum.edn" in src


def test_transition_matrix_uses_single_source():
    """REQ-KG-020: every status in the matrix is within :states, and the
    loader REJECTS a transitions map naming an out-of-source status."""
    edn_states, _ = _edn_states_and_transitions()

    named = set(claim_validator.VALID_TRANSITIONS.keys())
    for targets in claim_validator.VALID_TRANSITIONS.values():
        named |= set(targets)
    assert named <= edn_states

    # Synthetic source whose :transitions names a status absent from :states.
    bad = (
        "{:states [:proposed :verified]"
        " :transitions {:proposed #{:verified :ghost}}}"
    )
    with pytest.raises(claim_validator.ClaimVocabularyError):
        claim_validator._load_status_enum_text(bad)


def test_json_schema_matches_edn_source():
    """Drift guard: the acknowledged JSON-schema status enum copy equals the
    single EDN source as a set."""
    edn_states, _ = _edn_states_and_transitions()
    schema = json.loads(
        (ASSETS / "claim-record.schema.json").read_text(encoding="utf-8")
    )
    schema_enum = set(schema["properties"]["status"]["enum"])
    assert schema_enum == edn_states


def test_malformed_edn_raises_vocabulary_error():
    with pytest.raises(claim_validator.ClaimVocabularyError):
        claim_validator._load_status_enum_text("{not valid edn :::}")


def test_missing_states_key_raises_vocabulary_error():
    with pytest.raises(claim_validator.ClaimVocabularyError):
        claim_validator._load_status_enum_text("{:transitions {}}")
