"""Contract tests for the cozo_store seam (REQ-KG-002, REQ-KG-011).

These tests pin the backend-agnostic interface (`in_memory`/`load`/`query`/
`relations`) and the schema->relation creation guarantee. They are the only
place the seam's behaviour is exercised end to end against the embedded store.
"""
from __future__ import annotations

import re
from pathlib import Path

import edn_format
import pytest

from scripts.cozo_store import CozoStore, StubBackend

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "assets" / "kg-schema.edn"
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"


def _schema_entity_names_snake() -> set[str]:
    doc = edn_format.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    entities = doc[edn_format.Keyword("entities")]
    items = entities.dict.items() if hasattr(entities, "dict") else entities.items()
    return {k.name.replace("-", "_") for k, _ in items}


def test_query_returns_rows() -> None:
    """The public seam returns rows for an EDN query (REQ-KG-002/007)."""
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    store.load(
        "claim",
        [
            {"id": "clm-1", "canonical-text": "x", "status": "verified"},
            {"id": "clm-2", "canonical-text": "y", "status": "proposed"},
        ],
    )
    rows = store.query_edn(
        "(defquery :v :find [?id] "
        ':where [[?c :claim/id ?id] [?c :claim/status "verified"]])'
    )
    assert rows == [["clm-1"]]


def test_query_edn_compiles_and_runs() -> None:
    """REQ-KG-002/007: the public seam accepts EDN, not CozoScript.

    ``query_edn`` compiles the booklogic EDN to CozoScript INTERNALLY (the
    compile target never leaks to the consumer) and runs it. A consumer holding
    only EDN must get the right rows back.
    """
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    store.load(
        "claim",
        [
            {"id": "clm-1", "canonical-text": "x", "status": "verified"},
            {"id": "clm-2", "canonical-text": "y", "status": "proposed"},
        ],
    )
    rows = store.query_edn(
        "(defquery :v :find [?id] "
        ':where [[?c :claim/id ?id] [?c :claim/status "verified"]])'
    )
    assert rows == [["clm-1"]]


def test_relations_conform_to_schema() -> None:
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    relations = store.relations()

    expected = _schema_entity_names_snake()
    # REQ-KG-011: a fresh store has EXACTLY the declared relations -- no more,
    # no fewer. Equality, not superset.
    assert relations == expected, (
        f"missing: {expected - relations}; extra: {relations - expected}"
    )

    # A name absent from the schema does not exist as a relation.
    assert "not_an_entity" not in relations
    # The kebab-original of a schema entity must NOT exist (only snake-cased).
    assert "code-node" not in relations
    assert "code_node" in relations


def test_rejects_rogue_relation() -> None:
    """REQ-KG-011: a relation absent from kg-schema.edn must not survive init.

    Seeding a backend with an extra relation and constructing a store over it
    must fail loudly, naming the offending relation, rather than silently
    adopting a rogue/stale relation as a false dependency.
    """
    backend = StubBackend()
    backend.create("rogue_relation", ["id"], {})
    with pytest.raises(ValueError, match="rogue_relation"):
        CozoStore(backend=backend, schema_path=SCHEMA_PATH)


def test_numeric_column_supports_comparison() -> None:
    """A column typed :float in the schema must compare against a Float literal.

    Regression: when every column was created as String, a numeric comparison
    (`confidence < 0.4`) raised a Cozo QueryException because a String cell
    cannot be compared to a Float. The schema :types map must drive the Cozo
    column type so numeric queries (P1 posterior-floor, confidence thresholds)
    work.
    """
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    store.load(
        "claim",
        [
            {"id": "clm-low", "canonical-text": "x", "confidence": 0.3},
            {"id": "clm-high", "canonical-text": "y", "confidence": 0.9},
        ],
    )
    rows = store.query("?[id] := *claim{id, confidence}, confidence < 0.4")
    assert rows == [["clm-low"]]


def test_in_memory_does_not_emit_pandas_traceback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A successful Cozo run must not log a pandas ModuleNotFoundError.

    pycozo's Client defaults to ``dataframe=True`` and logs a pandas import
    traceback when pandas is absent, even though the run succeeds. Constructing
    the store with ``dataframe=False`` suppresses that noise. We capture the
    ``pycozo.client`` logger at the source (robust to pytest's stderr capture)
    and assert no pandas record was emitted, plus a working trivial query.
    """
    import logging

    with caplog.at_level(logging.DEBUG, logger="pycozo.client"):
        store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
        rows = store.query("?[x] <- [[1]]")
    assert rows == [[1]]
    assert "pandas" not in caplog.text


def test_no_module_bypasses_seam() -> None:
    """REQ-KG-002b: only cozo_store.py may import pycozo.

    Cozo->Asami stays a one-module swap only if no other script reaches around
    the seam. Scan the scripts tree offline and fail on any pycozo import found
    outside cozo_store.py.
    """
    pat = re.compile(r"^\s*(?:import\s+pycozo|from\s+pycozo)\b", re.MULTILINE)
    offenders: list[str] = []
    for py in SCRIPTS_DIR.rglob("*.py"):
        if py.name == "cozo_store.py":
            continue
        if pat.search(py.read_text(encoding="utf-8")):
            offenders.append(str(py))
    assert not offenders, f"pycozo imported outside the seam: {offenders}"


def test_stub_backend_satisfies_contract() -> None:
    """REQ-KG-007: the same public calls work against the in-memory StubBackend.

    The stub lets later tasks unit-test without the embedded Cozo and proves the
    Backend protocol is honoured: identical load/query calls, identical result.
    This exercises the INTERNAL raw-script runner (``query``) — the StubBackend
    is a narrow query-shape oracle that does not parse compiled-EDN CozoScript,
    so it is the retained internal-script coverage alongside the EDN seam.
    """
    store = CozoStore(backend=StubBackend(), schema_path=SCHEMA_PATH)
    store.load("claim", [{"id": "clm-1", "status": "verified"}])
    rows = store.query('?[id] := *claim{id, status}, status == "verified"')
    assert rows == [["clm-1"]]


def test_stub_comparison_against_null_raises() -> None:
    """A StubBackend ordered comparison against a null cell must RAISE.

    Real Cozo raises a QueryException ("Evaluation of expression failed") when a
    comparison operator (<, <=, >, >=) is applied to a null cell. The stub must
    mirror that so it stays a faithful oracle for P1 numeric queries; silently
    returning "no match" would hide queries that fail against the real store.
    Equality (==) null-handling is unchanged (null simply doesn't match).
    """
    store = CozoStore(backend=StubBackend(), schema_path=SCHEMA_PATH)
    store.load(
        "claim",
        [
            {"id": "clm-null", "canonical-text": "x"},  # confidence omitted -> null
            {"id": "clm-low", "canonical-text": "y", "confidence": 0.3},
        ],
    )
    with pytest.raises(RuntimeError):
        store.query("?[id] := *claim{id, confidence}, confidence < 0.4")
