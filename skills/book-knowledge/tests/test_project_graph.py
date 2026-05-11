from datetime import datetime, timezone

from rdflib import Graph, Namespace
from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.ledger import append_claim
from scripts.project_graph import project_graph

TBF = Namespace("https://example.org/book-knowledge#")
PROV = Namespace("http://www.w3.org/ns/prov#")


def _verified(cid: str) -> dict:
    return {
        "claim_id": cid,
        "canonical_text": f"Claim canonical body for {cid}",
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.9,
        "source_spans": [{"doc_id": "small", "page_index": 1, "locator_text": "locator text"}],
        "derived_from": [],
        "supports_chapters": [],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def test_project_graph_emits_trig_with_claims(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    append_claim(layout, _verified("clm-2026-000001"))
    project_graph(layout)
    assert layout.dataset.exists()
    g = Graph()
    g.parse(layout.dataset, format="trig")
    claims = list(g.triples((None, TBF.status, None)))
    assert len(claims) >= 1


def test_project_graph_writes_provenance(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    record = _verified("clm-2026-000001")
    record["derived_from"] = ["clm-1999-999999"]
    append_claim(layout, record)
    project_graph(layout)
    g = Graph()
    g.parse(layout.dataset, format="trig")
    derivations = list(g.triples((None, PROV.wasDerivedFrom, None)))
    assert len(derivations) >= 1


def test_project_graph_skips_superseded(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    record = _verified("clm-2026-000001")
    record["status"] = "superseded"
    append_claim(layout, record)
    project_graph(layout)
    g = Graph()
    g.parse(layout.dataset, format="trig")
    statuses = [str(o) for s, p, o in g.triples((None, TBF.status, None))]
    assert "superseded" not in statuses
