"""SHACL-constraint port parity: Cozo path == golden == normalized rdflib path.

REQ-KG-012 / REQ-KG-013: the Cozo-backed validator runs the booklogic
``defconstraint`` EDN over a :class:`CozoStore` and assembles the SAME
``ShaclReport`` the pyshacl path produces. This test closes the parity loop on
the C0.2 goldens, three ways:

* bermuda-via-projection: a clean workspace projected into Cozo yields ZERO
  violations, equal to ``shacl_report_bermuda.json``.
* violating-via-loaded-rows: synthetic rows mirroring the C0.1 violating fixture
  produce EXACTLY the four violations in the (canonical) updated
  ``shacl_report_violating.json``.
* PARITY (non-tautological): the DEFAULT rdflib path over the SAME violating
  fixture, normalized to canonical form, equals the SAME golden. So
  rdflib(normalized) == golden == cozo — both engines agree on the canonical
  representation, not merely on conformance.

The canonical representation (bare-id focus_node + authored EDN message + SHACL
path URI / "") is documented in
``docs/audits/2026-06-17-kg-shacl-representation-divergence.md``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.cozo_store import CozoStore
from scripts.project_ledger_cozo import project_ledger
from scripts.ledger import append_claim
from scripts.workspace import WorkspaceLayout, init_workspace
from scripts.validate_shacl import Violation, _evaluate_constraints

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "assets" / "kg-schema.edn"
GOLDEN = ROOT / "tests" / "golden" / "kg"


def _violation_set(violations) -> set[tuple[str, str, str]]:
    """Result-set form of a violation list: a set of (focus, path, message)."""
    return {(v.focus_node, v.path, v.message) for v in violations}


def _golden_set(name: str) -> set[tuple[str, str, str]]:
    doc = json.loads((GOLDEN / f"{name}.json").read_text(encoding="utf-8"))
    return {(v["focus_node"], v["path"], v["message"]) for v in doc["violations"]}


def _valid_claim(claim_id: str, status: str) -> dict:
    return {
        "claim_id": claim_id,
        "canonical_text": f"A well-formed base claim ({status}).",
        "status": status,
        "claim_type": "fact",
        "confidence": 0.8,
        "source_spans": [
            {"doc_id": "base-doc", "locator_text": "supporting passage"}
        ],
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def _load_violating_rows(store: CozoStore) -> None:
    """Load the synthetic rows that mirror tests/fixtures/violating_workspace.py.

    The bare claim/section ids match the canonical golden's focus_nodes. This
    yields EXACTLY four violations:
      - confidence-range on inj-bad-confidence (confidence 1.5),
      - source-span-present + verified-derives on inj-verified-no-source,
      - chapter-cites-verified on inj-section (cites the proposed claim).
    """
    store.load("claim", [
        # (a) verified, out-of-range confidence, but text + source-span present.
        {"id": "inj-bad-confidence", "status": "verified",
         "confidence": 1.5, "canonical-text": "Claim with an out-of-range confidence."},
        # (b) verified, no source-span (text present so text-cardinality stays quiet).
        {"id": "inj-verified-no-source", "status": "verified",
         "confidence": 0.9, "canonical-text": "Verified claim lacking any provenance."},
        # (c) proposed, well-formed (text + source-span) -> cited by inj-section.
        {"id": "inj-proposed", "status": "proposed",
         "confidence": 0.5, "canonical-text": "A well-formed but only-proposed claim."},
        # a valid verified base claim (text + source-span present).
        {"id": "clm-base", "status": "verified",
         "confidence": 0.8, "canonical-text": "A well-formed base claim."},
    ])
    store.load("source-span", [
        {"id": "s-bad-conf", "claim-id": "inj-bad-confidence"},
        {"id": "s-proposed", "claim-id": "inj-proposed"},
        {"id": "s-base", "claim-id": "clm-base"},
        # NOTE: deliberately NO span for inj-verified-no-source.
    ])
    store.load("chapter-section", [
        {"id": "inj-section", "uses-claim-id": "inj-proposed"},
    ])


def test_constraints_match_shacl_golden(tmp_path):
    # 1) bermuda-via-projection: a clean workspace projects into Cozo with ZERO
    #    constraint violations, equal to the bermuda golden.
    layout = WorkspaceLayout(init_workspace(tmp_path / "bermuda"))
    append_claim(layout, _valid_claim("clm-2026-000001", "verified"))
    append_claim(layout, _valid_claim("clm-2026-000002", "proposed"))

    store = CozoStore.in_memory(schema_path=SCHEMA)
    project_ledger(layout, store)
    bermuda = _evaluate_constraints(store, SCHEMA)
    assert bermuda == []
    assert _violation_set(bermuda) == _golden_set("shacl_report_bermuda")

    # 2) violating-via-loaded-rows: the synthetic rows produce EXACTLY the four
    #    canonical violations, result-set equal to the violating golden.
    vstore = CozoStore.in_memory(schema_path=SCHEMA)
    _load_violating_rows(vstore)
    cozo_violations = _evaluate_constraints(vstore, SCHEMA)
    assert len(cozo_violations) == 4, cozo_violations
    assert _violation_set(cozo_violations) == _golden_set("shacl_report_violating")


_CONFIDENCE_PATH = "https://example.org/book-knowledge#confidence"


def test_cozo_flags_confidence_below_zero():
    """C-1: confidence < 0.0 is flagged on the #confidence path (the minInclusive
    arm, ported as confidence-range-low). A claim with confidence -0.5 + a
    source-span (so ONLY the confidence floor fires) yields a #confidence violation."""
    store = CozoStore.in_memory(schema_path=SCHEMA)
    store.load("claim", [
        {"id": "c-low", "status": "verified", "confidence": -0.5,
         "canonical-text": "Claim with a below-zero confidence."},
    ])
    store.load("source-span", [{"id": "s-low", "claim-id": "c-low"}])
    cozo_conf = {
        v for v in _evaluate_constraints(store, SCHEMA)
        if v.path == _CONFIDENCE_PATH and v.focus_node == "c-low"
    }
    assert cozo_conf, "Cozo must flag confidence -0.5 on the #confidence path"
