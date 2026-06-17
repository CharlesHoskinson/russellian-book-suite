"""Determinism pin for the projector + query seam (REQ-KG-008).

Proves and enforces the canonical-ordering contract P1 (REQ-KG-006) relies on:

  - Projected relations are *byte-identical*: building two fresh stores from the
    SAME ledger and dumping the ``claim`` / ``source_span`` relations under a
    canonical serialization yields identical bytes.
  - Query result *sets* are stable: the SAME query against two stores compares
    equal after a canonical sort (result-set equality = unordered multiset after
    canonical sort, per the spec's Definitions).

If these pass out of the box, determinism already holds (the projector mints
stable span ids and ``load`` is an upsert keyed on the identity column); the
tests then stand as a regression pin. The canonical helpers live here so the
contract is expressed once and reused by P1.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.cozo_store import CozoStore
from scripts.ledger import append_claim
from scripts.project_ledger_cozo import project_ledger
from scripts.workspace import WorkspaceLayout, init_workspace

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "assets" / "kg-schema.edn"

# Relation -> its full ordered column list (key first), used to dump every row.
_CLAIM_COLS = [
    "id",
    "canonical_text",
    "status",
    "claim_type",
    "semantic_class",
    "confidence",
    "p_prior",
    "p_posterior",
    "load_bearing",
    "axiom",
    "pin_low_confidence",
    "created_at",
    "last_verified_at",
]
_SPAN_COLS = ["id", "claim_id", "doc_id", "node_id", "page_index", "locator_text"]


def _canonical(rows: list[list]) -> str:
    """Canonical serialization of a result set.

    Result-set equality is an unordered multiset compared after a canonical
    sort (spec Definitions). Sort by each row's JSON encoding (total order over
    heterogeneous cells) then dump the whole thing with ``sort_keys`` so the
    bytes are stable regardless of the backend's row order.
    """
    encoded = sorted(json.dumps(r, sort_keys=True) for r in rows)
    return json.dumps(encoded, sort_keys=True)


def _claim(claim_id: str, status: str = "verified", **overrides) -> dict:
    record = {
        "claim_id": claim_id,
        "canonical_text": "a sufficiently long canonical text",
        "status": status,
        "claim_type": "fact",
        "confidence": 0.8,
        "source_spans": [
            {"doc_id": "doc-1", "locator_text": "the source locator text"}
        ],
        "created_at": "2026-06-16T00:00:00+00:00",
    }
    record.update(overrides)
    return record


def _seed_ledger(tmp_path: Path) -> WorkspaceLayout:
    """A small workspace: three projected (verified, non-superseded) claims."""
    root = init_workspace(tmp_path)
    layout = WorkspaceLayout(root)
    append_claim(layout, _claim("clm-2026-000001"))
    append_claim(
        layout,
        _claim(
            "clm-2026-000002",
            source_spans=[
                {"doc_id": "doc-2", "locator_text": "another locator text here"},
                {"doc_id": "doc-3", "locator_text": "yet a third locator text"},
            ],
        ),
    )
    append_claim(layout, _claim("clm-2026-000003", status="proposed"))
    return layout


def _projected_store(layout: WorkspaceLayout) -> CozoStore:
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_ledger(layout, store)
    return store


def _dump_relation(store: CozoStore, relation: str, cols: list[str]) -> str:
    col_list = ", ".join(cols)
    rows = store.query(f"?[{col_list}] := *{relation}{{{col_list}}}")
    return _canonical(rows)


def test_projected_relations_byte_identical(tmp_path: Path) -> None:
    """REQ-KG-008: two fresh projections of the same ledger dump identically."""
    layout = _seed_ledger(tmp_path / "ws")

    store_a = _projected_store(layout)
    store_b = _projected_store(layout)

    for relation, cols in (("claim", _CLAIM_COLS), ("source_span", _SPAN_COLS)):
        dump_a = _dump_relation(store_a, relation, cols)
        dump_b = _dump_relation(store_b, relation, cols)
        assert dump_a == dump_b, f"{relation} dump differs across runs"
        # Sanity: there is actually data being compared (not two empty dumps).
        assert dump_a != _canonical([])


def test_query_result_canonically_stable(tmp_path: Path) -> None:
    """REQ-KG-008: a multi-row query is result-set equal across stores.

    Three projected claims => three rows, so ordering genuinely matters. After
    the canonical sort the two result sets must be byte-identical.
    """
    layout = _seed_ledger(tmp_path / "ws")
    store_a = _projected_store(layout)
    store_b = _projected_store(layout)

    query = "?[id, status] := *claim{id, status}"
    rows_a = store_a.query(query)
    rows_b = store_b.query(query)

    assert len(rows_a) == 3  # multiple rows: order actually matters
    assert _canonical(rows_a) == _canonical(rows_b)

    # Stable against itself, too (re-running the same query on one store).
    assert _canonical(store_a.query(query)) == _canonical(store_a.query(query))
