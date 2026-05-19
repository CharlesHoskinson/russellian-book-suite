"""REQ-LLMLIFT-040, 043, 044, 046: :backend :llm lift routing through
ingest_ledger.

The osmotic_pressure ingest walker must dispatch on each spec's :backend
keyword. `:backend :regex` (or absent) routes through the regex path
(unchanged). `:backend :llm` routes through `_llm_lift.cached_extract`,
schema-validates the proposal, and either emits a `:kind :expression`
atom (match) or a `:kind :defect :reason :llm-lift-rejected` atom
(REQ-LLMLIFT-043).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts._edn_reader import Keyword  # noqa: E402
from scripts._io import read_edn_file  # noqa: E402
from scripts.ingest_ledger import ingest  # noqa: E402

_KW_ATOMS = Keyword("atoms")
_KW_KIND = Keyword("kind")
_KW_REASON = Keyword("reason")
_KW_PREDICATE = Keyword("predicate")
_KW_VALUE = Keyword("value")
_KW_DEFECT = Keyword("defect")
_KW_LLM_LIFT_REJECTED = Keyword("llm-lift-rejected")
_KW_EXPRESSION = Keyword("expression")
_KW_ID = Keyword("id")


def _make_llm_predicates_edn(tmp_path: Path, canned_response: str) -> Path:
    """Write a minimal predicates.edn + booklogic-schema.edn pair where
    the single lift declares :backend :llm. The actual LLM provider is
    stubbed via NEUROSYM_LLM_PROVIDER=stub, but StubLift returns "{}"
    by default — so the integration shape we want comes from monkey-
    patching `get_provider` inside the test to return a stub with the
    canned response.

    Returns the predicates.edn path; the schema lives next to it.
    """
    rules = tmp_path / "rules"
    rules.mkdir()
    schema = rules / "booklogic-schema.edn"
    schema.write_text(
        '{:version 1 :sorts [:solution] '
        ':predicates {:osmotic-pressure-pa {:arg-sorts [:solution] :return :real}}}',
        encoding="utf-8",
    )
    preds = rules / "predicates.edn"
    preds.write_text(
        '{:version 1 :predicates {'
        ':osmotic-pressure-pa {:patterns [] '
        ':predicate :osmotic-pressure-pa :subject :s '
        ':value-kind :real :word-to-int {} '
        ':backend :llm :lift-id "L-osm-llm-001" '
        ':emit-template "(fact ?cid :solution :osmotic-pressure-pa ?v)"}}}',
        encoding="utf-8",
    )
    return preds


def _make_ledger(tmp_path: Path) -> Path:
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps({
            "claim_id": "c-llm-001",
            "claim_type": "fact",
            "canonical_text": "osmotic pressure is 1200 Pa",
            "status": "verified",
            "confidence": 1.0,
            "source_spans": [],
            "supports_chapters": [],
        }) + "\n",
        encoding="utf-8",
    )
    return ledger


def test_llm_backend_routes_to_provider_and_emits_match(
    tmp_path, monkeypatch
):
    """REQ-LLMLIFT-040, 042, 046: a `:backend :llm` lift routes through
    cached_extract; a schema-valid proposal arrives at the atomspace as
    `:kind :expression` (identical shape to a regex-extracted atom)."""
    # Disable cache so the stub is consulted fresh.
    monkeypatch.delenv("NEUROSYM_LLM_CACHE", raising=False)
    monkeypatch.setenv("NEUROSYM_LLM_PROVIDER", "stub")

    # Monkey-patch `get_provider` so the lift sees a stub with our canned
    # response (the bare `NEUROSYM_LLM_PROVIDER=stub` default StubLift
    # returns {} which is not a valid atom proposal).
    from scripts import _llm_lift  # type: ignore

    canned = json.dumps({
        "predicate": ":osmotic-pressure-pa",
        "subject": ":s",
        "value": 1200.0,
    })
    monkeypatch.setattr(
        _llm_lift, "get_provider",
        lambda *a, **kw: _llm_lift.StubLift(canned_response=canned),
    )

    preds = _make_llm_predicates_edn(tmp_path, canned)
    ledger = _make_ledger(tmp_path)
    out = tmp_path / "claims.edn"

    n = ingest(ledger, preds, out)
    assert n == 1

    payload = read_edn_file(out)
    atoms = payload[_KW_ATOMS]
    assert len(atoms) == 1
    atom = atoms[0]
    # REQ-LLMLIFT-046: the atom shape must match the regex backend's
    # output — :kind :expression, with :predicate / :value / :subject.
    assert atom[_KW_KIND] == _KW_EXPRESSION
    assert atom[_KW_PREDICATE] == Keyword("osmotic-pressure-pa")
    assert atom[_KW_VALUE] == 1200.0


def test_llm_backend_schema_invalid_emits_defect_atom(
    tmp_path, monkeypatch
):
    """REQ-LLMLIFT-043: when the LLM proposes an unknown predicate, the
    framework emits a :kind :defect :reason :llm-lift-rejected atom
    instead of silently falling back to OPAQUE."""
    monkeypatch.delenv("NEUROSYM_LLM_CACHE", raising=False)
    monkeypatch.setenv("NEUROSYM_LLM_PROVIDER", "stub")

    from scripts import _llm_lift  # type: ignore

    # Stub returns a predicate name NOT present in booklogic-schema.edn.
    canned = json.dumps({
        "predicate": ":hallucinated-predicate",
        "subject": ":s",
        "value": 99.9,
    })
    monkeypatch.setattr(
        _llm_lift, "get_provider",
        lambda *a, **kw: _llm_lift.StubLift(canned_response=canned),
    )

    preds = _make_llm_predicates_edn(tmp_path, canned)
    ledger = _make_ledger(tmp_path)
    out = tmp_path / "claims.edn"

    n = ingest(ledger, preds, out)
    assert n == 1
    payload = read_edn_file(out)
    atoms = payload[_KW_ATOMS]
    assert len(atoms) == 1
    atom = atoms[0]
    # REQ-LLMLIFT-043: defect atom with the canonical reason keyword.
    assert atom[_KW_KIND] == _KW_DEFECT
    assert atom[_KW_REASON] == _KW_LLM_LIFT_REJECTED
    # The offending predicate name is recorded for the verdict surface.
    assert "hallucinated-predicate" in str(atom[_KW_PREDICATE])


def test_regex_backend_still_works_when_llm_unconfigured(
    tmp_path, monkeypatch
):
    """REQ-LLMLIFT-046: mixed-backend support is the contract that lets
    incremental adoption work. A `:backend :regex` lift (or absent
    backend) must continue to behave exactly as it did before, with no
    LLM call made."""
    # No LLM env vars set — make sure the regex path doesn't accidentally
    # call into the provider.
    monkeypatch.delenv("NEUROSYM_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("NEUROSYM_LLM_CACHE", raising=False)

    n = ingest(
        PROJECT_ROOT / "fixtures" / "claims_clean.jsonl",
        PROJECT_ROOT / "rules" / "predicates.edn",
        tmp_path / "claims.edn",
    )
    assert n > 0
    payload = read_edn_file(tmp_path / "claims.edn")
    atoms = payload[_KW_ATOMS]
    # The clean fixtures should produce regex-matched expression atoms.
    expr_atoms = [a for a in atoms if a.get(_KW_KIND) == _KW_EXPRESSION]
    assert len(expr_atoms) > 0
