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


def test_discover_queries_picks_up_subdirs():
    from scripts.run_competency_queries import discover_queries
    ASSETS = Path(__file__).resolve().parent.parent / "assets"
    found = discover_queries(ASSETS)
    classes = {c for c, _, _ in found}
    assert "coverage" in classes
    assert "consistency" in classes
    names_in_coverage = {n for c, n, _ in found if c == "coverage"}
    assert "chapter_evidence_coverage" in names_in_coverage
    names_in_consistency = {n for c, n, _ in found if c == "consistency"}
    assert "contradiction_scan" in names_in_consistency


def test_defeasible_meta_yaml_loads():
    import yaml
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent / "assets" / "queries" / "defeasible" / "_meta.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert "rebuttal-presence" in data
    assert data["rebuttal-presence"]["severity"] in ("critical", "important", "minor")


def test_defeasible_queries_parse():
    from pathlib import Path
    from rdflib.plugins.sparql import prepareQuery
    qdir = Path(__file__).resolve().parent.parent / "assets" / "queries" / "defeasible"
    for q in qdir.glob("*.rq"):
        prepareQuery(q.read_text(encoding="utf-8"))  # raises on syntax error


def test_defeasible_query_emits_warning_not_failure(tmp_path, monkeypatch):
    """Warning-mode behavior: when BLOCKING_DEFEASIBLE is False, defeasible fires
    surface as warnings rather than raising. This configuration remains valid
    after the Phase 4 promotion to True default."""
    import json
    import scripts.run_competency_queries as mod
    from scripts.workspace import init_workspace, WorkspaceLayout
    from scripts.project_graph import project_graph
    monkeypatch.setattr(mod, "BLOCKING_DEFEASIBLE", False)
    layout = WorkspaceLayout(init_workspace(tmp_path))
    layout.ledger.write_text(json.dumps({
        "claim_id": "clm-2026-000001", "canonical_text": "Bermuda fact.",
        "status": "verified", "claim_type": "fact", "confidence": 0.8,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "created_at": "2026-05-11T00:00:00Z",
        "load_bearing": True, "supports_chapters": ["ch07"]
    }) + "\n", encoding="utf-8")
    project_graph(layout)
    result = mod.run_competency_queries(layout)
    assert "warnings" in result
    warnings = result["warnings"]
    names = {w["query"] for w in warnings}
    assert "rebuttal-presence" in names


def test_defeasible_critical_fire_hard_fails_when_blocking(tmp_path):
    """Phase 4 default behavior: severity=critical defeasible fires hard-fail."""
    import json
    import pytest
    from scripts.workspace import init_workspace, WorkspaceLayout
    from scripts.project_graph import project_graph
    from scripts.run_competency_queries import run_competency_queries
    layout = WorkspaceLayout(init_workspace(tmp_path))
    layout.ledger.write_text(json.dumps({
        "claim_id": "clm-2026-000001", "canonical_text": "Bermuda fact.",
        "status": "verified", "claim_type": "fact", "confidence": 0.8,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "created_at": "2026-05-11T00:00:00Z",
        "load_bearing": True, "supports_chapters": ["ch07"]
    }) + "\n", encoding="utf-8")
    project_graph(layout)
    with pytest.raises(RuntimeError, match="rebuttal-presence"):
        run_competency_queries(layout)


def test_defeasible_exception_queries_guard(tmp_path, monkeypatch):
    """Non-empty exception_queries must raise NotImplementedError until implemented."""
    import json
    import scripts.run_competency_queries as mod
    from scripts.workspace import init_workspace, WorkspaceLayout
    from scripts.project_graph import project_graph
    import pytest

    layout = WorkspaceLayout(init_workspace(tmp_path))
    # Seed a load-bearing claim that would fire rebuttal-presence.
    layout.ledger.write_text(json.dumps({
        "claim_id": "clm-2026-000001", "canonical_text": "Bermuda fact.",
        "status": "verified", "claim_type": "fact", "confidence": 0.8,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "created_at": "2026-05-11T00:00:00Z",
        "load_bearing": True, "supports_chapters": ["ch07"],
    }) + "\n", encoding="utf-8")
    project_graph(layout)

    # _load_defeasible_meta takes assets_root: Path; monkeypatch ignores it.
    monkeypatch.setattr(mod, "_load_defeasible_meta", lambda assets_root: {
        "rebuttal-presence": {"severity": "critical",
                              "default_satisfied": True,
                              "exception_queries": ["some-other-query"]},
    })
    with pytest.raises(NotImplementedError, match="exception_queries"):
        mod.run_competency_queries(layout)
