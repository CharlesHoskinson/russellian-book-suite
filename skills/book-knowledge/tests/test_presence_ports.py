"""P2.4 presence constraints over the Cozo path — status/confidence minCount.

The EDN->Cozo constraint port flags a claim missing its status or confidence
(``status-present`` / ``confidence-present``, minCount-via-negation), and a
wrong-typed confidence cannot enter the typed Float? column at all (load-time
error, not a silent conform). The rdflib parity legs were removed with the legacy
pyshacl path in P5.4a; these are the Cozo-side assertions.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.cozo_store import CozoStore
from scripts.validate_shacl import _evaluate_constraints

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "assets" / "kg-schema.edn"

_STATUS_PATH = "https://example.org/book-knowledge#status"
_CONFIDENCE_PATH = "https://example.org/book-knowledge#confidence"
_STATUS_PRESENT_MSG = "Claim must have a status value (minCount 1)."
_CONFIDENCE_PRESENT_MSG = "Claim must have a confidence value (minCount 1)."


def test_cozo_flags_missing_status():
    """A claim with a null status is a violation on the #status path."""
    store = CozoStore.in_memory(schema_path=SCHEMA)
    store.load("claim", [
        # status omitted -> null; text + confidence present so ONLY status-present fires.
        {"id": "c-no-status", "confidence": 0.7,
         "canonical-text": "Claim with no status."},
    ])
    store.load("source-span", [{"id": "s-no-status", "claim-id": "c-no-status"}])
    hits = [v for v in _evaluate_constraints(store, SCHEMA)
            if v.focus_node == "c-no-status" and v.path == _STATUS_PATH]
    assert hits, "missing status must be flagged"
    assert hits[0].message == _STATUS_PRESENT_MSG


def test_cozo_flags_missing_confidence():
    """A claim with a null confidence is a violation on the #confidence path."""
    store = CozoStore.in_memory(schema_path=SCHEMA)
    store.load("claim", [
        # confidence omitted -> null; text + status present so ONLY confidence-present fires.
        {"id": "c-no-conf", "status": "proposed",
         "canonical-text": "Claim with no confidence."},
    ])
    store.load("source-span", [{"id": "s-no-conf", "claim-id": "c-no-conf"}])
    hits = [v for v in _evaluate_constraints(store, SCHEMA)
            if v.focus_node == "c-no-conf" and v.path == _CONFIDENCE_PATH]
    assert hits, "missing confidence must be flagged"
    assert hits[0].message == _CONFIDENCE_PRESENT_MSG


def test_wrong_typed_confidence_raises_on_load():
    """A non-decimal confidence cannot enter the typed Float? column — CozoStore.load
    RAISES rather than silently conforming. Pinned so the behaviour can't drift to a
    silent-conform; only synthetic/corrupt data reaches it (the JSON record schema
    types confidence as a number on every real write)."""
    store = CozoStore.in_memory(schema_path=SCHEMA)
    with pytest.raises(Exception):  # pycozo QueryException, surfaced via the seam
        store.load("claim", [{"id": "c-bad", "status": "verified",
                              "confidence": "not-a-number", "canonical-text": "x"}])
