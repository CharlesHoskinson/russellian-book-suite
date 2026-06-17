"""P2.4 — Cozo presence (minCount) parity for status & confidence + message re-key.

External audit (2026-06-17) finding: the EDN->Cozo port carried the value-violation
constraints (status sh:in, confidence range) and two minCount negations
(text-cardinality, source-span-present), but NOT the ``tbf:status`` /
``tbf:confidence`` minCount checks. So under ``KG_BACKEND=cozo`` a claim missing
its status or confidence CONFORMED, while pyshacl flagged it — a gate that silently
weakens at the P5.3 default flip.

These tests pin the closure:

* the Cozo path now flags a status-less / confidence-less claim, on the same
  ``#status`` / ``#confidence`` path pyshacl reports;
* both engines AGREE on the full canonical ``(focus, path, message)`` triple for a
  missing value — which is only possible once the rdflib message remap is keyed on
  ``(path, sh:sourceConstraintComponent)`` rather than bare ``sh:path``: the new
  minCount constraints collide on path with ``status-enum`` (``#status``) and
  ``confidence-range`` (``#confidence``), so a path-only key would mislabel them
  (internal audit I-2, activated by this task).
"""
from __future__ import annotations

from pathlib import Path

from rdflib import Dataset, Literal, URIRef, XSD
from rdflib.namespace import RDF

from scripts.cozo_store import CozoStore
from scripts.ledger import append_claim
from scripts.project_graph import BASE, PROV, SCHEMA as SCH, TBF, project_graph
from scripts.workspace import WorkspaceLayout, init_workspace
from scripts.validate_shacl import _evaluate_constraints, validate_shacl

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "assets" / "kg-schema.edn"

_STATUS_PATH = "https://example.org/book-knowledge#status"
_CONFIDENCE_PATH = "https://example.org/book-knowledge#confidence"

_STATUS_PRESENT_MSG = "Claim must have a status value (minCount 1)."
_CONFIDENCE_PRESENT_MSG = "Claim must have a confidence value (minCount 1)."
_STATUS_ENUM_MSG = (
    "Claim status must be one of: proposed, verified, disputed, "
    "superseded, refuted."
)


def _valid_claim(claim_id: str, status: str) -> dict:
    return {
        "claim_id": claim_id,
        "canonical_text": f"A well-formed base claim ({status}).",
        "status": status,
        "claim_type": "fact",
        "confidence": 0.8,
        "source_spans": [{"doc_id": "base-doc", "locator_text": "passage"}],
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def _inject_claim(layout: WorkspaceLayout, claim_id: str, triples) -> None:
    """Append one injected claim (its triples) to the projected TriG dataset.

    Mirrors tests/fixtures/violating_workspace.py: a conforming base is already
    projected; we add raw triples for ONE otherwise-complete claim so only the
    intended constraint fires. ``layout.shapes`` is left empty so validate_shacl
    falls back to the shipped assets/shapes.ttl.
    """
    ds = Dataset(default_union=True)
    if layout.dataset.exists() and layout.dataset.stat().st_size > 0:
        ds.parse(layout.dataset, format="trig")
    ds.bind("tbf", TBF)
    ds.bind("prov", PROV)
    ds.bind("schema", SCH)
    g = ds.default_graph
    for t in triples:
        g.add(t)
    layout.dataset.parent.mkdir(parents=True, exist_ok=True)
    ds.serialize(destination=str(layout.dataset), format="trig")


def _missing_status_workspace(tmp_path) -> WorkspaceLayout:
    layout = WorkspaceLayout(init_workspace(tmp_path / "missing-status"))
    append_claim(layout, _valid_claim("clm-2026-000001", "verified"))
    project_graph(layout)
    c = URIRef(f"{BASE}claims/inj-missing-status")
    src = URIRef(f"{BASE}sources/inj-doc#span-ms")
    _inject_claim(layout, "inj-missing-status", [
        (c, RDF.type, TBF.Claim), (c, RDF.type, PROV.Entity),
        (c, SCH.text, Literal("Claim with no status.", datatype=XSD.string)),
        (c, TBF.confidence, Literal("0.7", datatype=XSD.decimal)),
        (c, SCH.dateCreated, Literal("2026-01-02T00:00:00+00:00", datatype=XSD.dateTime)),
        (src, RDF.type, PROV.Entity),
        (c, PROV.wasDerivedFrom, src), (c, TBF.hasSourceSpan, src),
    ])
    return layout


def test_cozo_flags_missing_status(tmp_path):
    """A claim with a null status is a violation under the Cozo path (#status)."""
    store = CozoStore.in_memory(schema_path=SCHEMA)
    store.load("claim", [
        # status omitted -> null; text + confidence present so ONLY status-present fires.
        {"id": "c-no-status", "confidence": 0.7,
         "canonical-text": "Claim with no status."},
    ])
    store.load("source-span", [{"id": "s-no-status", "claim-id": "c-no-status"}])
    violations = _evaluate_constraints(store, SCHEMA)
    hits = [v for v in violations
            if v.focus_node == "c-no-status" and v.path == _STATUS_PATH]
    assert hits, violations
    assert hits[0].message == _STATUS_PRESENT_MSG


def test_cozo_flags_missing_confidence(tmp_path):
    """A claim with a null confidence is a violation under the Cozo path (#confidence)."""
    store = CozoStore.in_memory(schema_path=SCHEMA)
    store.load("claim", [
        # confidence omitted -> null; text + status present so ONLY confidence-present fires.
        {"id": "c-no-conf", "status": "proposed",
         "canonical-text": "Claim with no confidence."},
    ])
    store.load("source-span", [{"id": "s-no-conf", "claim-id": "c-no-conf"}])
    violations = _evaluate_constraints(store, SCHEMA)
    hits = [v for v in violations
            if v.focus_node == "c-no-conf" and v.path == _CONFIDENCE_PATH]
    assert hits, violations
    assert hits[0].message == _CONFIDENCE_PRESENT_MSG


def test_both_engines_agree_on_missing_status(tmp_path, monkeypatch):
    """rdflib(normalized) and cozo produce the SAME canonical triple for missing status."""
    # cozo leg
    store = CozoStore.in_memory(schema_path=SCHEMA)
    store.load("claim", [
        {"id": "inj-missing-status", "confidence": 0.7,
         "canonical-text": "Claim with no status."},
    ])
    store.load("source-span", [{"id": "s-ms", "claim-id": "inj-missing-status"}])
    cozo = {(v.focus_node, v.path, v.message) for v in _evaluate_constraints(store, SCHEMA)}
    assert ("inj-missing-status", _STATUS_PATH, _STATUS_PRESENT_MSG) in cozo

    # rdflib leg (default backend), normalized inside validate_shacl
    layout = _missing_status_workspace(tmp_path)
    monkeypatch.delenv("KG_BACKEND", raising=False)
    report = validate_shacl(layout)
    rdflib = {(v.focus_node, v.path, v.message) for v in report.violations}
    assert ("inj-missing-status", _STATUS_PATH, _STATUS_PRESENT_MSG) in rdflib


def test_status_minCount_and_sh_in_messages_do_not_collide(tmp_path, monkeypatch):
    """status-present (minCount) and status-enum (sh:in) share #status but must keep
    distinct authored messages — the path-keyed remap would collapse them (I-2)."""
    # An out-of-vocab status fires status-enum (sh:in); a missing status fires
    # status-present (minCount). Both are on #status; the messages must differ.
    layout = WorkspaceLayout(init_workspace(tmp_path / "status-mix"))
    append_claim(layout, _valid_claim("clm-2026-000001", "verified"))
    project_graph(layout)
    bogus = URIRef(f"{BASE}claims/inj-bogus-status")
    bsrc = URIRef(f"{BASE}sources/inj-doc#span-b")
    _inject_claim(layout, "inj-bogus-status", [
        (bogus, RDF.type, TBF.Claim), (bogus, RDF.type, PROV.Entity),
        (bogus, SCH.text, Literal("Claim with an out-of-vocab status.", datatype=XSD.string)),
        (bogus, TBF.status, Literal("frobnicated")),
        (bogus, TBF.confidence, Literal("0.6", datatype=XSD.decimal)),
        (bogus, SCH.dateCreated, Literal("2026-01-05T00:00:00+00:00", datatype=XSD.dateTime)),
        (bsrc, RDF.type, PROV.Entity),
        (bogus, PROV.wasDerivedFrom, bsrc), (bogus, TBF.hasSourceSpan, bsrc),
    ])
    monkeypatch.delenv("KG_BACKEND", raising=False)
    report = validate_shacl(layout)
    status_msgs = {v.message for v in report.violations if v.path == _STATUS_PATH}
    assert _STATUS_ENUM_MSG in status_msgs, report.violations
    assert _STATUS_PRESENT_MSG not in status_msgs  # sh:in must NOT get the minCount message
