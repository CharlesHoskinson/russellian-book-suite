import pytest

pytestmark = pytest.mark.windows_canary

from datetime import datetime, timezone
from pathlib import Path

from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.ledger import append_claim
from scripts.run_competency_queries import run_competency_queries


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


def test_unsupported_claims_query_returns_nothing_when_clean(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    append_claim(layout, _verified("clm-2026-000001"))
    findings = run_competency_queries(layout)
    assert findings["unsupported_claims"] == []


def test_chapter_evidence_coverage_counts_per_chapter(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    append_claim(layout, _verified("clm-2026-000001", supports_chapters=["ch-01"]))
    append_claim(layout, _verified("clm-2026-000002", supports_chapters=["ch-01"]))
    append_claim(layout, _verified("clm-2026-000003", supports_chapters=["ch-02"]))
    findings = run_competency_queries(layout)
    coverage = {row[0]: int(row[1]) for row in findings["chapter_evidence_coverage"]}
    assert any(k.endswith("ch-01") and v == 2 for k, v in coverage.items())
    assert any(k.endswith("ch-02") and v == 1 for k, v in coverage.items())


def test_runner_writes_report_file(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
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


def test_query_manifest_loads():
    import yaml
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent / "assets" / "kg-queries" / "_meta.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert data["rebuttal-presence"]["class"] == "defeasible"
    assert data["rebuttal-presence"]["severity"] in ("critical", "important", "minor")


def test_defeasible_query_emits_warning_not_failure(tmp_path, monkeypatch):
    """Warning-mode behavior: when BLOCKING_DEFEASIBLE is False, defeasible fires
    surface as warnings rather than raising. This configuration remains valid
    after the Phase 4 promotion to True default."""
    import json
    import scripts.run_competency_queries as mod
    from scripts.workspace import init_workspace, WorkspaceLayout
    monkeypatch.setattr(mod, "BLOCKING_DEFEASIBLE", False)
    layout = WorkspaceLayout(init_workspace(tmp_path))
    layout.ledger.write_text(json.dumps({
        "claim_id": "clm-2026-000001", "canonical_text": "Bermuda fact.",
        "status": "verified", "claim_type": "fact", "confidence": 0.8,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "created_at": "2026-05-11T00:00:00Z",
        "load_bearing": True, "supports_chapters": ["ch07"]
    }) + "\n", encoding="utf-8")
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
    from scripts.run_competency_queries import run_competency_queries
    layout = WorkspaceLayout(init_workspace(tmp_path))
    layout.ledger.write_text(json.dumps({
        "claim_id": "clm-2026-000001", "canonical_text": "Bermuda fact.",
        "status": "verified", "claim_type": "fact", "confidence": 0.8,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "created_at": "2026-05-11T00:00:00Z",
        "load_bearing": True, "supports_chapters": ["ch07"]
    }) + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="rebuttal-presence"):
        run_competency_queries(layout)


def test_cli_main_returns_clean_gate_code_on_hard_fail(tmp_path, capsys):
    """When BLOCKING_DEFEASIBLE fires, main() must surface a clean gate-failure
    message and a distinct non-zero exit code, not an unhandled traceback."""
    import json
    from scripts.workspace import init_workspace, WorkspaceLayout
    from scripts.run_competency_queries import main
    layout = WorkspaceLayout(init_workspace(tmp_path))
    layout.ledger.write_text(json.dumps({
        "claim_id": "clm-2026-000001", "canonical_text": "Bermuda fact.",
        "status": "verified", "claim_type": "fact", "confidence": 0.8,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "created_at": "2026-05-11T00:00:00Z",
        "load_bearing": True, "supports_chapters": ["ch07"]
    }) + "\n", encoding="utf-8")
    rc = main(["run_competency_queries.py", str(tmp_path)])
    assert rc == 3
    captured = capsys.readouterr()
    assert "GATE FAILED" in captured.err
    assert "rebuttal-presence" in captured.err


def test_posterior_floor_fires_on_low_posterior(tmp_path, monkeypatch):
    """posterior-floor query must return rows when a chapter-supporting claim
    has p_posterior < 0.4 without pin_low_confidence."""
    import json
    import scripts.run_competency_queries as mod
    from scripts.workspace import init_workspace, WorkspaceLayout
    monkeypatch.setattr(mod, "BLOCKING_DEFEASIBLE", False)
    layout = WorkspaceLayout(init_workspace(tmp_path))
    layout.ledger.write_text(json.dumps({
        "claim_id": "clm-2026-000001", "canonical_text": "Low confidence claim.",
        "status": "verified", "claim_type": "fact", "confidence": 0.3,
        "p_posterior": 0.3,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "supports_chapters": ["ch07"],
        "created_at": "2026-05-13T00:00:00Z",
    }) + "\n", encoding="utf-8")
    result = mod.run_competency_queries(layout)
    warnings = result.get("warnings", [])
    names = {w["query"] for w in warnings}
    assert "posterior-floor" in names


def test_posterior_floor_skips_pinned_claim(tmp_path, monkeypatch):
    """A claim with pin_low_confidence: true should NOT fire posterior-floor."""
    import json
    import scripts.run_competency_queries as mod
    from scripts.workspace import init_workspace, WorkspaceLayout
    monkeypatch.setattr(mod, "BLOCKING_DEFEASIBLE", False)
    layout = WorkspaceLayout(init_workspace(tmp_path))
    layout.ledger.write_text(json.dumps({
        "claim_id": "clm-2026-000001", "canonical_text": "Pinned low claim.",
        "status": "verified", "claim_type": "fact", "confidence": 0.3,
        "p_posterior": 0.3, "pin_low_confidence": True,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "supports_chapters": ["ch07"],
        "created_at": "2026-05-13T00:00:00Z",
    }) + "\n", encoding="utf-8")
    result = mod.run_competency_queries(layout)
    warnings = result.get("warnings", [])
    names = {w["query"] for w in warnings}
    assert "posterior-floor" not in names


def test_rebuttal_presence_skips_axiom_claim(tmp_path, monkeypatch):
    """A claim with axiom: true should NOT fire rebuttal-presence even if load-bearing."""
    import json
    import scripts.run_competency_queries as mod
    from scripts.workspace import init_workspace, WorkspaceLayout
    monkeypatch.setattr(mod, "BLOCKING_DEFEASIBLE", False)
    layout = WorkspaceLayout(init_workspace(tmp_path))
    layout.ledger.write_text(json.dumps({
        "claim_id": "clm-2026-000001", "canonical_text": "An axiom load-bearing claim.",
        "status": "verified", "claim_type": "fact", "confidence": 0.95,
        "load_bearing": True, "axiom": True,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "supports_chapters": ["ch07"],
        "created_at": "2026-05-13T00:00:00Z",
    }) + "\n", encoding="utf-8")
    result = mod.run_competency_queries(layout)
    warnings = result.get("warnings", [])
    names = {w["query"] for w in warnings}
    assert "rebuttal-presence" not in names


def test_defeasible_exception_queries_guard(tmp_path, monkeypatch):
    """Non-empty exception_queries must raise NotImplementedError until implemented."""
    import json
    import scripts.run_competency_queries as mod
    from scripts.workspace import init_workspace, WorkspaceLayout
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

    # The manifest supplies the defeasible severity + exception_queries.
    monkeypatch.setattr(mod, "_load_manifest", lambda: {
        "rebuttal-presence": {"class": "defeasible", "severity": "critical",
                              "exception_queries": ["some-other-query"]},
    })
    with pytest.raises(NotImplementedError, match="exception_queries"):
        mod.run_competency_queries(layout)


def test_default_backend_is_cozo(tmp_path):
    """P5.4: run_competency_queries is Cozo-only — it sources facts from the ledger
    projection (no RDF dataset path remains). A clean workspace returns the
    established shape with no defects."""
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    append_claim(layout, _verified("clm-2026-000001"))
    findings = run_competency_queries(layout)
    assert findings["unsupported_claims"] == []
    assert "warnings" in findings
