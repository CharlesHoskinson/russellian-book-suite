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
from scripts.project_graph import project_graph
from scripts.workspace import WorkspaceLayout, init_workspace
from scripts.validate_shacl import (
    Violation,
    _evaluate_constraints,
    _normalize_pyshacl_violations,
    validate_shacl,
)

from tests.fixtures.violating_workspace import build_violating_workspace

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


def test_constraints_match_shacl_golden(tmp_path, monkeypatch):
    # 1) bermuda-via-projection: a clean workspace projects into Cozo with ZERO
    #    constraint violations, equal to the bermuda golden.
    layout = WorkspaceLayout(init_workspace(tmp_path / "bermuda"))
    append_claim(layout, _valid_claim("clm-2026-000001", "verified"))
    append_claim(layout, _valid_claim("clm-2026-000002", "proposed"))
    project_graph(layout)

    store = CozoStore.in_memory(schema_path=SCHEMA)
    project_ledger(layout, store)
    bermuda = _evaluate_constraints(store, SCHEMA)
    assert bermuda == []
    assert _violation_set(bermuda) == _golden_set("shacl_report_bermuda")

    # 2) violating-via-loaded-rows: the synthetic rows produce EXACTLY the four
    #    canonical violations, result-set equal to the updated violating golden.
    vstore = CozoStore.in_memory(schema_path=SCHEMA)
    _load_violating_rows(vstore)
    cozo_violations = _evaluate_constraints(vstore, SCHEMA)
    assert len(cozo_violations) == 4, cozo_violations
    assert _violation_set(cozo_violations) == _golden_set("shacl_report_violating")

    # 3) PARITY (non-tautological): the DEFAULT rdflib path over the SAME
    #    violating fixture, normalized to canonical form, equals the SAME golden.
    #    This proves rdflib(normalized) == golden == cozo.
    vlayout = build_violating_workspace(tmp_path)
    monkeypatch.delenv("KG_BACKEND", raising=False)
    rdflib_report = validate_shacl(vlayout)  # default backend = rdflib
    normalized = _normalize_pyshacl_violations(rdflib_report.violations)
    assert _violation_set(normalized) == _golden_set("shacl_report_violating")


_CONFIDENCE_PATH = "https://example.org/book-knowledge#confidence"


def _build_low_confidence_workspace(tmp_path) -> WorkspaceLayout:
    """A minimal workspace whose projected TriG has ONE claim with confidence -0.5.

    Reuses the rdflib-injection technique of
    ``tests/fixtures/violating_workspace.py``: build a conforming base via
    ``append_claim`` + ``project_graph``, then inject a single otherwise-complete
    claim (text + status + source-span) whose ``tbf:confidence`` is below 0.0, so
    ONLY the confidence range fires. ``layout.shapes`` is left empty so
    ``validate_shacl`` falls back to the shipped ``assets/shapes.ttl``.
    """
    from rdflib import Dataset, Literal, URIRef, XSD
    from rdflib.namespace import RDF
    from scripts.project_graph import BASE, PROV, SCHEMA as SCH, TBF, project_graph

    layout = WorkspaceLayout(init_workspace(tmp_path / "low-conf"))
    append_claim(layout, _valid_claim("clm-2026-000001", "verified"))
    project_graph(layout)

    ds = Dataset(default_union=True)
    if layout.dataset.exists() and layout.dataset.stat().st_size > 0:
        ds.parse(layout.dataset, format="trig")
    ds.bind("tbf", TBF)
    ds.bind("prov", PROV)
    ds.bind("schema", SCH)
    default = ds.default_graph

    low = URIRef(f"{BASE}claims/inj-low-confidence")
    low_src = URIRef(f"{BASE}sources/inj-doc#span-low")
    for t in [
        (low, RDF.type, TBF.Claim),
        (low, RDF.type, PROV.Entity),
        (low, SCH.text, Literal("Claim with a below-zero confidence.", datatype=XSD.string)),
        (low, TBF.status, Literal("verified")),
        (low, TBF.confidence, Literal("-0.5", datatype=XSD.decimal)),
        (low, SCH.dateCreated, Literal("2026-01-02T00:00:00+00:00", datatype=XSD.dateTime)),
        (low_src, RDF.type, PROV.Entity),
        (low, PROV.wasDerivedFrom, low_src),
        (low, TBF.hasSourceSpan, low_src),
    ]:
        default.add(t)

    layout.dataset.parent.mkdir(parents=True, exist_ok=True)
    ds.serialize(destination=str(layout.dataset), format="trig")
    return layout


def test_both_engines_flag_confidence_below_zero(tmp_path, monkeypatch):
    """C-1: confidence < 0.0 is non-conforming under BOTH the Cozo and rdflib engines.

    Before C-1, ``confidence-range.edn`` only filtered ``> 1.0`` while pyshacl
    enforced both ``sh:minInclusive 0.0`` and ``sh:maxInclusive 1.0`` — so a
    ``confidence -0.5`` claim was rdflib-non-conforming but Cozo-conforming
    (opposite verdicts). With ``confidence-range-low`` ported, both engines flag
    it, on the same ``#confidence`` path. This test proves the agreement.
    """
    # -- Cozo leg: a claim with confidence -0.5 + a source-span (so only the
    #    confidence floor fires) -> a #confidence violation on c-low.
    store = CozoStore.in_memory(schema_path=SCHEMA)
    store.load("claim", [
        {"id": "c-low", "status": "verified", "confidence": -0.5,
         "canonical-text": "Claim with a below-zero confidence."},
    ])
    store.load("source-span", [{"id": "s-low", "claim-id": "c-low"}])
    cozo_violations = _evaluate_constraints(store, SCHEMA)
    cozo_conf = {
        v for v in cozo_violations
        if v.path == _CONFIDENCE_PATH and v.focus_node == "c-low"
    }
    assert cozo_conf, cozo_violations  # Cozo flags it (conforms would be False)

    # -- rdflib leg: project the same below-zero confidence into TriG, validate
    #    via pyshacl (default backend) -> non-conforming with a #confidence
    #    violation present.
    layout = _build_low_confidence_workspace(tmp_path)
    monkeypatch.delenv("KG_BACKEND", raising=False)
    rdflib_report = validate_shacl(layout)
    assert rdflib_report.conforms is False
    rdflib_conf = [
        v for v in rdflib_report.violations if v.path == _CONFIDENCE_PATH
    ]
    assert rdflib_conf, rdflib_report.violations

    # -- Both engines AGREE: each flags confidence -0.5 on the #confidence path.
    #    This closes C-1.
    assert cozo_conf and rdflib_conf


def test_normalizer_maps_raw_pyshacl_to_canonical():
    """I-1: the normalizer is an audited transform (raw pyshacl -> canonical).

    The canonical golden was rewritten by P2.3, so it no longer freezes the
    pre-port pyshacl output. ``shacl_report_violating_raw.json`` freezes that raw
    output (recovered from commit 46790fe). Loading it, building ``Violation``
    objects, and applying ``_normalize_pyshacl_violations`` must yield a result
    set EQUAL to the canonical ``shacl_report_violating.json`` — proving the
    normalizer is the explicit raw->canonical map, not an unstated identity. After
    C-1, the raw confidence message ``"Value is not <= Literal(...)"`` normalizes
    (via the #confidence path) to ``"Claim confidence must be in [0.0, 1.0]."``.
    """
    raw_doc = json.loads(
        (GOLDEN / "shacl_report_violating_raw.json").read_text(encoding="utf-8")
    )
    raw_violations = [
        Violation(
            focus_node=v["focus_node"], path=v["path"], message=v["message"],
            component=v.get("component", ""),
        )
        for v in raw_doc["violations"]
    ]
    normalized = _normalize_pyshacl_violations(raw_violations)
    assert _violation_set(normalized) == _golden_set("shacl_report_violating")
