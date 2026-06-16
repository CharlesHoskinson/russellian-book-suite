"""Contract tests for the cozo_store seam (REQ-KG-002, REQ-KG-011).

These tests pin the backend-agnostic interface (`in_memory`/`load`/`query`/
`relations`) and the schema->relation creation guarantee. They are the only
place the seam's behaviour is exercised end to end against the embedded store.
"""
from __future__ import annotations

from pathlib import Path

import edn_format
import pytest

from scripts.cozo_store import CozoStore

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "assets" / "kg-schema.edn"


def _schema_entity_names_snake() -> set[str]:
    doc = edn_format.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    entities = doc[edn_format.Keyword("entities")]
    items = entities.dict.items() if hasattr(entities, "dict") else entities.items()
    return {k.name.replace("-", "_") for k, _ in items}


def test_query_returns_rows() -> None:
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    store.load(
        "claim",
        [
            {"id": "clm-1", "canonical-text": "x", "status": "verified"},
            {"id": "clm-2", "canonical-text": "y", "status": "proposed"},
        ],
    )
    rows = store.query('?[id] := *claim{id, status}, status == "verified"')
    assert rows == [["clm-1"]]


def test_relations_conform_to_schema() -> None:
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    relations = store.relations()

    expected = _schema_entity_names_snake()
    assert expected <= relations, f"missing relations: {expected - relations}"

    # A name absent from the schema does not exist as a relation.
    assert "not_an_entity" not in relations
    # The kebab-original of a schema entity must NOT exist (only snake-cased).
    assert "code-node" not in relations
    assert "code_node" in relations
