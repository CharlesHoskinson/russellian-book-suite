"""Tests for design-intelligence audit artifact generation (REQ-KG-054/056)."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.build_design_kg_audit import _build_study_map, build_design_kg_audit

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "design-kg"


def test_build_design_kg_audit_writes_reproducible_artifact(tmp_path: Path) -> None:
    out_dir = tmp_path / "audit"

    result = build_design_kg_audit(
        root=FIXTURE_ROOT,
        out_dir=out_dir,
        date="2026-06-19",
        commit="fixture-commit",
        graphify_version="graphify fixture",
    )

    assert result == {
        "artifact_dir": str(out_dir),
        "requirements": 1,
        "design_decisions": 4,
        "tests": 1,
        "ci_workflows": 1,
        "ci_jobs": 1,
        "traceability_links": 6,
        "promoted_links": 6,
        "evidence_only_links": 0,
        "graph_nodes": 2,
        "graph_edges": 1,
    }

    summary = json.loads((out_dir / "snapshot-summary.json").read_text())
    assert summary["metadata"]["commit"] == "fixture-commit"
    assert summary["metadata"]["graphify_version"] == "graphify fixture"
    assert "projection_commands" in summary["metadata"]
    assert summary["metadata"]["report_paths"]["queries"] == "queries.md"
    assert summary["metadata"]["report_paths"]["study_map"] == "study-map.md"
    assert summary["counts"]["design_scenarios"] == 1
    assert summary["counts"]["traceability_links"] == 6

    readme = (out_dir / "README.md").read_text()
    coverage = (out_dir / "coverage-map.md").read_text()
    findings = (out_dir / "findings.md").read_text()
    queries = (out_dir / "queries.md").read_text()
    study_map = json.loads((out_dir / "study-map.json").read_text())

    assert "fixture-commit" in readme
    assert "graph nodes" in readme
    assert "Community" in coverage
    assert "fixture_module" in coverage
    assert "coverage-gaps" in findings
    assert "impact" in queries
    assert "source_path" in queries
    assert "AI-facing priority map" in readme
    assert study_map["summary"] == {
        "capability_count": 0,
        "active_coverage_gaps": 0,
        "archived_coverage_gaps": 0,
        "stale_evidence_links": 0,
        "top_priority": None,
    }


def test_study_map_prioritizes_active_gaps_over_archived_noise() -> None:
    study_map = _build_study_map(
        {
            "coverage-gaps": [
                {
                    "capability": "active-capability",
                    "missing": "implementation,test",
                    "requirement_id": "REQ-ACT-001",
                    "source_path": "openspec/specs/active-capability/spec.md",
                    "source_line": 10,
                },
                {
                    "capability": "archive-only",
                    "missing": "implementation,test,ci",
                    "requirement_id": "REQ-OLD-001",
                    "source_path": (
                        "openspec/changes/archive/2026-06-01-old/specs/"
                        "archive-only/spec.md"
                    ),
                    "source_line": 20,
                },
            ],
            "stale-docs": [
                {
                    "from_id": "openspec:active-capability:REQ-ACT-002",
                    "link_kind": "requirement-implemented-by",
                    "witness": "active_symbol",
                    "source_path": "openspec/specs/active-capability/spec.md",
                    "source_line": 30,
                }
            ],
        }
    )

    assert study_map["summary"] == {
        "capability_count": 2,
        "active_coverage_gaps": 1,
        "archived_coverage_gaps": 1,
        "stale_evidence_links": 1,
        "top_priority": "active-capability",
    }
    assert study_map["priorities"][0]["recommended_action"] == (
        "add or promote traceability for active requirements "
        "covering implementation, test"
    )
    assert study_map["priorities"][0]["examples"][0]["archived"] is False
    assert study_map["priorities"][1]["recommended_action"] == (
        "confirm archived requirements are historical, then keep them out of active design gates"
    )
    assert study_map["priorities"][1]["examples"][0]["archived"] is True
