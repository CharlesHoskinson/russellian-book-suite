"""Smoke tests for the design-intelligence KG fixture (REQ-KG-047/048/050)."""
from __future__ import annotations

import json
from pathlib import Path

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "design-kg"


def test_design_kg_fixture_has_required_inputs() -> None:
    expected = [
        "openspec/specs/sample-capability/spec.md",
        "docs/design.md",
        "tests/test_fixture_pipeline.py",
        ".github/workflows/ci.yml",
        "src/fixture.py",
        "graphify/graph.json",
    ]
    for rel in expected:
        assert (FIXTURE_ROOT / rel).is_file(), f"missing fixture input: {rel}"


def test_design_kg_fixture_links_requirement_test_ci_and_code() -> None:
    spec = (FIXTURE_ROOT / "openspec/specs/sample-capability/spec.md").read_text(
        encoding="utf-8"
    )
    test_file = (FIXTURE_ROOT / "tests/test_fixture_pipeline.py").read_text(
        encoding="utf-8"
    )
    workflow = (FIXTURE_ROOT / ".github/workflows/ci.yml").read_text(
        encoding="utf-8"
    )
    graph = json.loads((FIXTURE_ROOT / "graphify/graph.json").read_text(
        encoding="utf-8"
    ))

    assert "REQ-KG-901" in spec
    assert "test_REQ_KG_901_fixture_requirement" in spec
    assert "test_REQ_KG_901_fixture_requirement" in test_file
    assert "design-kg-required" in workflow
    assert {node["id"] for node in graph["nodes"]} == {
        "fixture_module",
        "fixture_entrypoint",
    }
    assert graph["links"] == [
        {
            "source": "fixture_module",
            "target": "fixture_entrypoint",
            "relation": "contains",
            "confidence": 1.0,
            "weight": 1.0,
        }
    ]
