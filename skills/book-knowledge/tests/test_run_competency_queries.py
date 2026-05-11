from datetime import datetime, timezone
from pathlib import Path

from rdflib import Dataset, Literal, URIRef, Namespace, XSD
from rdflib.namespace import RDF
from urllib.parse import quote

from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.ledger import append_claim
from scripts.project_graph import project_graph
from scripts.run_competency_queries import run_competency_queries

TBF = Namespace("https://example.org/book-knowledge#")


def _verified(cid: str, **kwargs) -> dict:
    base = {
        "claim_id": cid,
        "canonical_text": f"placeholder claim body for {cid}",
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.9,
        "source_spans": [{"doc_id": "small", "locator_text": "placeholder locator"}],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    base.update(kwargs)
    return base


def _add_chapter_typing(layout: WorkspaceLayout, chapters: list[str]) -> None:
    """Add rdf:type Chapter triples to the workspace dataset for the given chapters."""
    ds = Dataset(default_union=True)
    ds.parse(layout.dataset, format="trig")
    default = ds.graph(URIRef("https://example.org/book-knowledge/graphs/chapters"))
    for ch in chapters:
        default.add((URIRef(f"https://example.org/book-knowledge/chapters/{quote(ch)}"),
                     RDF.type, TBF.Chapter))
    ds.serialize(destination=str(layout.dataset), format="trig")


def test_unsupported_claims_query_returns_nothing_when_clean(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    append_claim(layout, _verified("clm-2026-000001"))
    project_graph(layout)
    findings = run_competency_queries(layout)
    assert findings["unsupported_claims"] == []


def test_chapter_evidence_coverage_counts_per_chapter(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    append_claim(layout, _verified("clm-2026-000001", supports_chapters=["ch-01"]))
    append_claim(layout, _verified("clm-2026-000002", supports_chapters=["ch-01"]))
    append_claim(layout, _verified("clm-2026-000003", supports_chapters=["ch-02"]))
    project_graph(layout)
    _add_chapter_typing(layout, ["ch-01", "ch-02"])
    findings = run_competency_queries(layout)
    coverage = {row[0]: int(row[1]) for row in findings["chapter_evidence_coverage"]}
    assert any(k.endswith("ch-01") and v == 2 for k, v in coverage.items())
    assert any(k.endswith("ch-02") and v == 1 for k, v in coverage.items())


def test_runner_writes_report_file(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    project_graph(layout)
    run_competency_queries(layout)
    reports = list(layout.graph_reports.glob("competency-*.md"))
    assert reports, "no competency report written"
