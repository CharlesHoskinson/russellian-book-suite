"""Project the claim ledger into a TriG dataset with PROV-O provenance."""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import quote

from rdflib import Dataset, Literal, Namespace, URIRef, XSD
from rdflib.namespace import RDF

from .counter_claims import read_counter_claims
from .ledger import read_claims
from .workspace import WorkspaceLayout

TBF = Namespace("https://example.org/book-knowledge#")
PROV = Namespace("http://www.w3.org/ns/prov#")
SCHEMA = Namespace("https://schema.org/")
BASE = "https://example.org/book-knowledge/"


def _claim_uri(claim_id: str) -> URIRef:
    return URIRef(f"{BASE}claims/{quote(claim_id)}")


def _source_uri(doc_id: str, locator_text: str) -> URIRef:
    return URIRef(f"{BASE}sources/{quote(doc_id)}#{quote(locator_text[:32])}")


def _latest_per_claim(records: list[dict]) -> list[dict]:
    latest: dict[str, dict] = {}
    for r in records:
        latest[r["claim_id"]] = r
    return list(latest.values())


def project_graph(layout: WorkspaceLayout) -> Path:
    ds = Dataset(default_union=True)
    ds.bind("tbf", TBF)
    ds.bind("prov", PROV)
    ds.bind("schema", SCHEMA)

    default = ds.default_graph
    for claim in _latest_per_claim(read_claims(layout)):
        if claim["status"] == "superseded":
            continue
        graph_name = URIRef(f"{BASE}graphs/claims/{quote(claim['claim_id'])}")
        cg = ds.graph(graph_name)
        c_uri = _claim_uri(claim["claim_id"])

        triples = [
            (c_uri, RDF.type, TBF.Claim),
            (c_uri, RDF.type, PROV.Entity),
            (c_uri, SCHEMA.text, Literal(claim["canonical_text"], datatype=XSD.string)),
            (c_uri, TBF.status, Literal(claim["status"])),
            (c_uri, TBF.confidence, Literal(claim["confidence"], datatype=XSD.decimal)),
            (c_uri, SCHEMA.dateCreated, Literal(claim["created_at"], datatype=XSD.dateTime)),
        ]

        for span in claim["source_spans"]:
            s_uri = _source_uri(span["doc_id"], span["locator_text"])
            triples.append((s_uri, RDF.type, PROV.Entity))
            triples.append((c_uri, PROV.wasDerivedFrom, s_uri))
            triples.append((c_uri, TBF.hasSourceSpan, s_uri))

        for derived in claim.get("derived_from", []):
            triples.append((c_uri, PROV.wasDerivedFrom, _claim_uri(derived)))

        for chapter in claim.get("supports_chapters", []):
            ch_uri = URIRef(f"{BASE}chapters/{quote(chapter)}")
            triples.append((c_uri, TBF.supportsChapter, ch_uri))

        for t in triples:
            cg.add(t)
            default.add(t)

        if "p_posterior" in claim:
            cg.add((c_uri, TBF.pPosterior, Literal(float(claim["p_posterior"]), datatype=XSD.decimal)))
            default.add((c_uri, TBF.pPosterior, Literal(float(claim["p_posterior"]), datatype=XSD.decimal)))

        if claim.get("load_bearing"):
            cg.add((c_uri, TBF.loadBearing, Literal(True)))
            default.add((c_uri, TBF.loadBearing, Literal(True)))

        if claim.get("axiom"):
            cg.add((c_uri, TBF.axiom, Literal(True)))
            default.add((c_uri, TBF.axiom, Literal(True)))

        if claim.get("pin_low_confidence"):
            cg.add((c_uri, TBF.pinLowConfidence, Literal(True)))
            default.add((c_uri, TBF.pinLowConfidence, Literal(True)))

        for conflict in claim.get("conflicts_with", []):
            cg.add((c_uri, TBF.conflictsWith, _claim_uri(conflict)))
            default.add((c_uri, TBF.conflictsWith, _claim_uri(conflict)))

    for cc in read_counter_claims(layout.root):
        cc_uri = URIRef(f"{BASE}counter-claims/{quote(cc['id'])}")
        default.add((cc_uri, RDF.type, TBF.CounterClaim))
        default.add((cc_uri, TBF.rebuts, _claim_uri(cc["target_claim_id"])))
        default.add((cc_uri, TBF.ccStatus, Literal(cc["status"])))

    layout.dataset.parent.mkdir(parents=True, exist_ok=True)
    ds.serialize(destination=str(layout.dataset), format="trig")
    return layout.dataset


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: project_graph.py <workspace-dir>", file=sys.stderr)
        return 2
    layout = WorkspaceLayout(Path(argv[1]))
    out = project_graph(layout)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
