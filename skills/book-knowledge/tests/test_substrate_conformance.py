"""Substrate conformance harness tests (REQ-KG-041..046)."""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.windows_canary

from scripts.cozo_store import Backend
from scripts.reference_datalog import ReferenceDatalogEvaluator, declared_subset
from scripts.substrate_conformance import (
    SubstrateConformanceHarness,
    SubstrateDivergenceError,
    canonical_json,
    load_fixtures,
)

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parents[1]
DOC = REPO_ROOT / "docs" / "operations" / "kg-substrate-switch-triggers.md"


class RecordingStore:
    """Minimal seam-shaped store used to prove harness routing."""

    def __init__(self) -> None:
        self.loaded: dict[str, list[dict]] = {}
        self.query_count = 0

    def load(self, relation: str, rows) -> None:
        self.loaded[relation] = [dict(row) for row in rows]

    def query_edn(self, edn_text: str):
        self.query_count += 1
        return ReferenceDatalogEvaluator(self.loaded).evaluate(edn_text)


def test_harness_runs_frozen_fixtures() -> None:
    """REQ-KG-041: frozen EDN fixtures run through the cozo_store seam shape."""
    stores: list[RecordingStore] = []

    def store_factory(schema_path: Path) -> RecordingStore:
        store = RecordingStore()
        stores.append(store)
        return store

    harness = SubstrateConformanceHarness(store_factory=store_factory)
    fixtures = load_fixtures()
    results = harness.run_all()

    assert {result.fixture for result in results} == {fixture.name for fixture in fixtures}
    assert len(stores) == len(fixtures)
    assert all(store.query_count == 1 for store in stores)
    assert all(store.loaded for store in stores)


def test_dual_run_result_set_equal() -> None:
    """REQ-KG-042: Cozo and the independent reference agree on frozen fixtures."""
    results = SubstrateConformanceHarness().run_all()

    assert {result.fixture for result in results} == {
        "contradiction-scan-basic",
        "posterior-floor-filter-negation",
    }
    assert all(
        canonical_json(result.cozo_rows) == canonical_json(result.reference_rows)
        for result in results
    )


def test_reference_backend_is_authoring_only() -> None:
    """REQ-KG-043: the reference evaluates a subset but is not production."""
    subset = declared_subset()
    reference = ReferenceDatalogEvaluator({})
    harness = SubstrateConformanceHarness()
    cozo_source = (SKILL_ROOT / "scripts" / "cozo_store.py").read_text(
        encoding="utf-8"
    )
    reference_source = (SKILL_ROOT / "scripts" / "reference_datalog.py").read_text(
        encoding="utf-8"
    )

    assert subset["name"] == "defquery-basic-v1"
    assert "aggregation" in subset["unsupported"]
    assert not isinstance(reference, Backend)
    assert harness.production_store == "CozoStore.in_memory"
    assert "ReferenceDatalogEvaluator" not in cozo_source
    assert "pycozo" not in reference_source


def test_canonical_ordering_deterministic() -> None:
    """REQ-KG-044: canonical ordering ignores backend row-emission order."""
    rows_a = [["b", 2], ["a", 1], ["a", 1]]
    rows_b = [["a", 1], ["b", 2], ["a", 1]]

    first = canonical_json(rows_a)
    second = canonical_json(rows_b)

    assert first == second
    assert first == '[["a",1],["a",1],["b",2]]'


def test_switch_trigger_doc_lists_triggers() -> None:
    """REQ-KG-045: substrate docs name every backend-switch trigger."""
    text = DOC.read_text(encoding="utf-8").lower()

    assert "python or platform support breaks" in text
    assert "unpatchable correctness or security issue" in text
    assert "reference backend reproduces the rule surface acceptably" in text
    assert "embedded / python-primary / offline constraints are relaxed" in text


def test_divergence_fails_and_names_rows() -> None:
    """REQ-KG-046: divergence names the fixture and symmetric-difference rows."""

    class DivergentReference:
        def __init__(self, relations) -> None:
            self._inner = ReferenceDatalogEvaluator(relations)

        def evaluate(self, edn_text: str):
            rows = self._inner.evaluate(edn_text)
            return rows + [["clm-2026-999998", "clm-2026-999999"]]

    fixture = next(
        item for item in load_fixtures() if item.name == "contradiction-scan-basic"
    )
    harness = SubstrateConformanceHarness(
        reference_factory=lambda relations: DivergentReference(relations)
    )

    with pytest.raises(SubstrateDivergenceError) as exc:
        harness.run_fixture(fixture)

    message = str(exc.value)
    assert "contradiction-scan-basic" in message
    assert "reference_only" in message
    assert "clm-2026-999998" in message
