"""Tests for the design-intelligence named query pack (REQ-KG-051/052)."""
from __future__ import annotations

from pathlib import Path

from scripts.cozo_store import CozoStore
from scripts.design_kg_queries import QUERY_NAMES, run_design_query
from scripts.project_design_kg import (
    project_design_docs,
    project_design_requirements,
    project_tests_and_ci,
    project_traceability_links,
)
from scripts.project_graphify import project_graphify

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "assets" / "kg-schema.edn"
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "design-kg"


def _fixture_store() -> CozoStore:
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_graphify(FIXTURE_ROOT / "graphify/graph.json", store)
    project_design_requirements(FIXTURE_ROOT, store)
    project_design_docs(FIXTURE_ROOT, store)
    project_tests_and_ci(FIXTURE_ROOT, store)
    project_traceability_links(FIXTURE_ROOT, store)
    return store


def _assert_provenance(rows: list[dict]) -> None:
    for row in rows:
        assert row["source_path"]
        assert isinstance(row["source_line"], int)
        assert row["source_line"] >= 1


def test_query_pack_declares_expected_names() -> None:
    assert QUERY_NAMES == (
        "impact",
        "why",
        "coverage-gaps",
        "stale-docs",
        "untested-god-nodes",
        "claim-grounding",
        "ci-gates",
    )


def test_fixture_queries_return_source_backed_rows() -> None:
    store = _fixture_store()

    impact = run_design_query(store, "impact", "src/fixture.py")
    why = run_design_query(store, "why", "REQ-KG-901")
    gates = run_design_query(store, "ci-gates", "sample-capability")

    assert {row["kind"] for row in impact} == {
        "decision-constrains-code",
        "requirement-implemented-by",
        "test-exercises-code",
    }
    assert {row["kind"] for row in why} == {
        "requirement",
        "scenario",
        "requirement-covered-by",
        "requirement-gated-by",
        "requirement-implemented-by",
    }
    assert gates == [
        {
            "query": "ci-gates",
            "kind": "requirement-gated-by",
            "requirement_id": "REQ-KG-901",
            "capability": "sample-capability",
            "ci_job_id": "ci-job:.github/workflows/ci.yml:design-kg-required",
            "ci_job_name": "design-kg-required",
            "required": True,
            "selector": "",
            "command": "python -m pytest tests/test_fixture_pipeline.py -q",
            "source_path": ".github/workflows/ci.yml",
            "source_line": 12,
        }
    ]

    for rows in (impact, why, gates):
        _assert_provenance(rows)


def test_coverage_gaps_report_unlinked_requirements() -> None:
    store = _fixture_store()
    store.load(
        "design-requirement",
        [
            {
                "id": "openspec:gap:REQ-KG-999",
                "requirement_id": "REQ-KG-999",
                "capability": "gap",
                "status": "fixture",
                "text": "This fixture requirement has no links.",
                "source_path": "openspec/specs/gap/spec.md",
                "source_line": 5,
            }
        ],
    )

    rows = run_design_query(store, "coverage-gaps")
    assert rows == [
        {
            "query": "coverage-gaps",
            "kind": "coverage-gap",
            "requirement_id": "REQ-KG-999",
            "capability": "gap",
            "missing": "implementation,test,ci",
            "source_path": "openspec/specs/gap/spec.md",
            "source_line": 5,
        }
    ]
    _assert_provenance(rows)


def test_stale_docs_reports_evidence_only_links() -> None:
    store = _fixture_store()
    store.load(
        "traceability-link",
        [
            {
                "id": "weak-doc-link",
                "from_id": "openspec:sample-capability:REQ-KG-901",
                "to_id": "fixture_entrypoint",
                "kind": "requirement-implemented-by",
                "confidence": 0.25,
                "witness": "fixture_entrypoint",
                "provenance": "deterministic:lexical-symbol",
                "promoted": False,
                "source_path": "openspec/specs/sample-capability/spec.md",
                "source_line": 5,
            }
        ],
    )

    rows = run_design_query(store, "stale-docs")
    assert rows == [
        {
            "query": "stale-docs",
            "kind": "evidence-only-link",
            "from_id": "openspec:sample-capability:REQ-KG-901",
            "to_id": "fixture_entrypoint",
            "link_kind": "requirement-implemented-by",
            "witness": "fixture_entrypoint",
            "provenance": "deterministic:lexical-symbol",
            "source_path": "openspec/specs/sample-capability/spec.md",
            "source_line": 5,
        }
    ]
    _assert_provenance(rows)


def test_untested_god_nodes_report_high_rank_nodes_without_tests() -> None:
    store = _fixture_store()
    store.load(
        "code-node",
        [{"id": "god", "label": "god.py", "source_file": "src/god.py", "rank": 0.95}],
    )

    rows = run_design_query(store, "untested-god-nodes")
    assert rows == [
        {
            "query": "untested-god-nodes",
            "kind": "untested-god-node",
            "code_id": "god",
            "label": "god.py",
            "source_path": "src/god.py",
            "source_line": 1,
            "rank": 0.95,
        }
    ]
    _assert_provenance(rows)


def test_claim_grounding_reports_code_claim_edges() -> None:
    store = _fixture_store()
    store.load(
        "claim",
        [
            {
                "id": "clm-kg-001",
                "canonical_text": "Fixture module supports the claim.",
                "status": "verified",
            }
        ],
    )
    store.load(
        "code-claim-link",
        [
            {
                "id": "fixture_module\x1fclm-kg-001\x1ffile-path",
                "code_id": "fixture_module",
                "claim_id": "clm-kg-001",
                "kind": "file-path",
            }
        ],
    )

    rows = run_design_query(store, "claim-grounding", "fixture_module")
    assert rows == [
        {
            "query": "claim-grounding",
            "kind": "claim-supported-by-code",
            "code_id": "fixture_module",
            "code_label": "fixture.py",
            "claim_id": "clm-kg-001",
            "claim_status": "verified",
            "claim_text": "Fixture module supports the claim.",
            "link_kind": "file-path",
            "source_path": "src/fixture.py",
            "source_line": 1,
        }
    ]
    _assert_provenance(rows)
