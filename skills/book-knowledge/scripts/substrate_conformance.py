"""Dual-run substrate conformance harness for frozen EDN fixtures."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .cozo_store import CozoStore
from .reference_datalog import ReferenceDatalogEvaluator

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = SKILL_ROOT / "assets" / "kg-schema.edn"
FIXTURE_DIR = SKILL_ROOT / "tests" / "fixtures" / "substrate-conformance"


class SubstrateDivergenceError(AssertionError):
    """Raised when Cozo and the reference evaluator disagree."""


@dataclass(frozen=True)
class ConformanceFixture:
    name: str
    query_path: Path
    relations: Mapping[str, Sequence[Mapping[str, Any]]]
    expected_rows: Sequence[Sequence[Any]]
    subset: str


@dataclass(frozen=True)
class ConformanceResult:
    fixture: str
    cozo_rows: list[list[Any]]
    reference_rows: list[list[Any]]
    canonical_json: str


def _row_key(row: Sequence[Any]) -> str:
    return json.dumps(list(row), sort_keys=True, separators=(",", ":"))


def canonical_rows(rows: Sequence[Sequence[Any]]) -> list[list[Any]]:
    """Return rows sorted by a backend-independent JSON row key."""
    return [json.loads(key) for key in sorted(_row_key(row) for row in rows)]


def canonical_json(rows: Sequence[Sequence[Any]]) -> str:
    """Byte-stable canonical serialization for result-set equality."""
    return json.dumps(canonical_rows(rows), sort_keys=True, separators=(",", ":"))


def load_fixtures(
    fixture_dir: Path = FIXTURE_DIR,
    *,
    skill_root: Path = SKILL_ROOT,
) -> list[ConformanceFixture]:
    """Load committed frozen fixture JSON files."""
    fixtures: list[ConformanceFixture] = []
    for path in sorted(Path(fixture_dir).glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        fixtures.append(
            ConformanceFixture(
                name=payload["name"],
                query_path=skill_root / payload["query_path"],
                relations=payload["relations"],
                expected_rows=payload.get("expected_rows", []),
                subset=payload["subset"],
            )
        )
    return fixtures


class SubstrateConformanceHarness:
    """Run frozen query fixtures against Cozo and the reference evaluator."""

    def __init__(
        self,
        *,
        schema_path: Path = SCHEMA_PATH,
        fixture_dir: Path = FIXTURE_DIR,
        store_factory: Callable[[Path], Any] | None = None,
        reference_factory: Callable[
            [Mapping[str, Sequence[Mapping[str, Any]]]], Any
        ] = ReferenceDatalogEvaluator,
    ) -> None:
        self.schema_path = Path(schema_path)
        self.fixture_dir = Path(fixture_dir)
        self.store_factory = store_factory or (
            lambda schema: CozoStore.in_memory(schema_path=schema)
        )
        self.reference_factory = reference_factory

    @property
    def production_store(self) -> str:
        return "CozoStore.in_memory"

    def run_all(self) -> list[ConformanceResult]:
        return [self.run_fixture(fixture) for fixture in load_fixtures(self.fixture_dir)]

    def run_fixture(self, fixture: ConformanceFixture) -> ConformanceResult:
        edn_text = fixture.query_path.read_text(encoding="utf-8")

        store = self.store_factory(self.schema_path)
        for relation, rows in fixture.relations.items():
            store.load(relation, rows)
        cozo_rows = store.query_edn(edn_text)

        reference = self.reference_factory(fixture.relations)
        reference_rows = reference.evaluate(edn_text)

        self._assert_equal(fixture.name, cozo_rows, reference_rows)
        if fixture.expected_rows:
            self._assert_expected(fixture.name, cozo_rows, fixture.expected_rows)

        return ConformanceResult(
            fixture=fixture.name,
            cozo_rows=canonical_rows(cozo_rows),
            reference_rows=canonical_rows(reference_rows),
            canonical_json=canonical_json(cozo_rows),
        )

    @staticmethod
    def _assert_expected(
        fixture: str,
        rows: Sequence[Sequence[Any]],
        expected: Sequence[Sequence[Any]],
    ) -> None:
        if _counter(rows) != _counter(expected):
            raise SubstrateDivergenceError(
                f"fixture {fixture!r} no longer matches committed expected rows: "
                f"actual={canonical_rows(rows)} expected={canonical_rows(expected)}"
            )

    @staticmethod
    def _assert_equal(
        fixture: str,
        cozo_rows: Sequence[Sequence[Any]],
        reference_rows: Sequence[Sequence[Any]],
    ) -> None:
        cozo = _counter(cozo_rows)
        reference = _counter(reference_rows)
        if cozo == reference:
            return
        cozo_only = _counter_rows(cozo - reference)
        reference_only = _counter_rows(reference - cozo)
        raise SubstrateDivergenceError(
            f"fixture {fixture!r} diverged: "
            f"cozo_only={cozo_only}; reference_only={reference_only}"
        )


def _counter(rows: Sequence[Sequence[Any]]) -> Counter[str]:
    return Counter(_row_key(row) for row in rows)


def _counter_rows(counter: Counter[str]) -> list[list[Any]]:
    expanded: list[list[Any]] = []
    for key, count in counter.items():
        expanded.extend(json.loads(key) for _ in range(count))
    return canonical_rows(expanded)
