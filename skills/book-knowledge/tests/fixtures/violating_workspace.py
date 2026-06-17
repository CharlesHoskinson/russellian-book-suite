"""Build a workspace whose projected TriG dataset is a *non-vacuous* SHACL failure.

This freezes a known-bad baseline before the SHACL->EDN port (Phase P2). A valid
claim ledger projected by ``project_graph`` always conforms, and ``append_claim``
rejects out-of-range or source-less claims at write time, so the violations here
cannot be produced through the public write path. Instead we build a realistic,
conforming base via ``append_claim`` + ``project_graph``, then inject three
deliberately-violating elements directly into the projected dataset with rdflib,
reusing the exact namespaces and triple shapes ``project_graph`` emits so that for
each injected node *only* the intended constraint fails:

(a) a claim with ``tbf:confidence`` outside 0.0-1.0 (but otherwise complete, incl.
    a valid source-span) -> only ``tbf:ClaimShape`` confidence range fires;
(b) a ``verified`` claim with no ``tbf:hasSourceSpan``/``prov:wasDerivedFrom`` ->
    the ``tbf:hasSourceSpan`` minCount AND the "Verified claims must derive..."
    ``sh:sparql`` both fire;
(c) a ``tbf:ChapterSection`` whose ``tbf:usesClaim`` points at a ``proposed``
    claim -> ``tbf:ChapterSectionShape`` fires.

The injected triples are fixed, so calling :func:`build_violating_workspace` on two
different ``tmp_path`` values yields equivalent violation sets. C0.2 imports this
helper to capture the SHACL golden, so the signature is load-bearing.
"""
from __future__ import annotations

from pathlib import Path

from rdflib import Dataset, Literal, URIRef, XSD
from rdflib.namespace import RDF

from scripts.ledger import append_claim
from scripts.project_graph import BASE, PROV, SCHEMA, TBF, project_graph
from scripts.workspace import WorkspaceLayout, init_workspace


def _valid_claim(claim_id: str, status: str) -> dict:
    """A fully schema-valid claim record with one real source-span."""
    return {
        "claim_id": claim_id,
        "canonical_text": f"A well-formed base claim ({status}).",
        "status": status,
        "claim_type": "fact",
        "confidence": 0.8,
        "source_spans": [
            {"doc_id": "base-doc", "locator_text": "supporting passage from the base document"}
        ],
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def _inject_violations(layout: WorkspaceLayout) -> None:
    """Load the conforming base TriG, add the three violating elements, re-serialize."""
    ds = Dataset(default_union=True)
    if layout.dataset.exists() and layout.dataset.stat().st_size > 0:
        ds.parse(layout.dataset, format="trig")
    ds.bind("tbf", TBF)
    ds.bind("prov", PROV)
    ds.bind("schema", SCHEMA)

    default = ds.default_graph

    # (a) Confidence out of range, but otherwise complete (valid source-span) so
    #     that ONLY tbf:ClaimShape's confidence range constraint fires.
    bad_conf = URIRef(f"{BASE}claims/inj-bad-confidence")
    conf_src = URIRef(f"{BASE}sources/inj-doc#span-a")
    for t in [
        (bad_conf, RDF.type, TBF.Claim),
        (bad_conf, RDF.type, PROV.Entity),
        (bad_conf, SCHEMA.text, Literal("Claim with an out-of-range confidence.", datatype=XSD.string)),
        (bad_conf, TBF.status, Literal("verified")),
        (bad_conf, TBF.confidence, Literal("1.5", datatype=XSD.decimal)),
        (bad_conf, SCHEMA.dateCreated, Literal("2026-01-02T00:00:00+00:00", datatype=XSD.dateTime)),
        (conf_src, RDF.type, PROV.Entity),
        (bad_conf, PROV.wasDerivedFrom, conf_src),
        (bad_conf, TBF.hasSourceSpan, conf_src),
    ]:
        default.add(t)

    # (b) Verified claim with NO source-span: fires both the tbf:hasSourceSpan
    #     minCount and the "Verified claims must derive..." sh:sparql.
    no_src = URIRef(f"{BASE}claims/inj-verified-no-source")
    for t in [
        (no_src, RDF.type, TBF.Claim),
        (no_src, RDF.type, PROV.Entity),
        (no_src, SCHEMA.text, Literal("Verified claim lacking any provenance.", datatype=XSD.string)),
        (no_src, TBF.status, Literal("verified")),
        (no_src, TBF.confidence, Literal("0.9", datatype=XSD.decimal)),
        (no_src, SCHEMA.dateCreated, Literal("2026-01-03T00:00:00+00:00", datatype=XSD.dateTime)),
    ]:
        default.add(t)

    # (c) ChapterSection citing a non-verified (proposed) claim: fires
    #     tbf:ChapterSectionShape. The proposed claim is otherwise well-formed
    #     (text, status, in-range confidence, source-span) so it does not itself
    #     trip tbf:ClaimShape.
    proposed = URIRef(f"{BASE}claims/inj-proposed")
    proposed_src = URIRef(f"{BASE}sources/inj-doc#span-c")
    section = URIRef(f"{BASE}sections/inj-section")
    for t in [
        (proposed, RDF.type, TBF.Claim),
        (proposed, RDF.type, PROV.Entity),
        (proposed, SCHEMA.text, Literal("A well-formed but only-proposed claim.", datatype=XSD.string)),
        (proposed, TBF.status, Literal("proposed")),
        (proposed, TBF.confidence, Literal("0.5", datatype=XSD.decimal)),
        (proposed, SCHEMA.dateCreated, Literal("2026-01-04T00:00:00+00:00", datatype=XSD.dateTime)),
        (proposed_src, RDF.type, PROV.Entity),
        (proposed, PROV.wasDerivedFrom, proposed_src),
        (proposed, TBF.hasSourceSpan, proposed_src),
        (section, RDF.type, TBF.ChapterSection),
        (section, TBF.usesClaim, proposed),
    ]:
        default.add(t)

    layout.dataset.parent.mkdir(parents=True, exist_ok=True)
    ds.serialize(destination=str(layout.dataset), format="trig")


def build_violating_workspace(tmp_path: Path) -> WorkspaceLayout:
    """Build, under ``tmp_path``, a workspace whose dataset has >=3 SHACL violations.

    Returns the :class:`WorkspaceLayout`. ``layout.shapes`` is intentionally left
    empty so ``validate_shacl`` falls back to the shipped ``assets/shapes.ttl``.
    """
    layout = WorkspaceLayout(init_workspace(tmp_path / "violating"))

    # Realistic, fully-conforming base so the dataset is non-trivial.
    append_claim(layout, _valid_claim("clm-2026-000001", "verified"))
    append_claim(layout, _valid_claim("clm-2026-000002", "proposed"))
    project_graph(layout)

    _inject_violations(layout)
    return layout
