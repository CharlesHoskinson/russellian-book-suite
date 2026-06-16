"""Tests for the ledger->cozo projector (REQ-KG-004).

`project_ledger` loads every latest-per-id VERIFIED claim and its source-spans
from the append-only ledger into the Cozo store's `claim` and `source_span`
relations, without touching the ledger file.
"""
from __future__ import annotations

from pathlib import Path

from scripts.cozo_store import CozoStore
from scripts.ledger import append_claim
from scripts.project_ledger_cozo import project_ledger
from scripts.workspace import WorkspaceLayout, init_workspace

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "assets" / "kg-schema.edn"


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


def test_projects_latest_verified_claims(tmp_path: Path) -> None:
    root = init_workspace(tmp_path / "ws")
    layout = WorkspaceLayout(root)
    append_claim(layout, _claim("clm-2026-000001"))

    before = layout.ledger.read_text(encoding="utf-8")

    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_ledger(layout, store)

    rows = store.query('?[id] := *claim{id, status}, status == "verified"')
    assert rows == [["clm-2026-000001"]]

    spans = store.query("?[claim_id] := *source_span{claim_id}")
    assert spans == [["clm-2026-000001"]]

    # Ledger untouched, byte-for-byte.
    assert layout.ledger.read_text(encoding="utf-8") == before


def test_typed_values_preserved(tmp_path: Path) -> None:
    root = init_workspace(tmp_path / "ws")
    layout = WorkspaceLayout(root)
    append_claim(
        layout,
        _claim(
            "clm-2026-000010",
            confidence=0.3,
            load_bearing=True,
            source_spans=[
                {
                    "doc_id": "doc-1",
                    "page_index": 7,
                    "locator_text": "the source locator text",
                }
            ],
        ),
    )

    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_ledger(layout, store)

    # Numeric comparison only works if confidence was stored as a real Float.
    low = store.query("?[id] := *claim{id, confidence}, confidence < 0.4")
    assert low == [["clm-2026-000010"]]

    bools = store.query("?[id] := *claim{id, load_bearing}, load_bearing == true")
    assert bools == [["clm-2026-000010"]]

    # page_index stored as a real Int.
    pages = store.query("?[page_index] := *source_span{page_index}, page_index == 7")
    assert pages == [[7]]


def test_only_latest_verified(tmp_path: Path) -> None:
    root = init_workspace(tmp_path / "ws")
    layout = WorkspaceLayout(root)

    # Claim A: proposed then flipped to superseded (terminal, non-verified).
    append_claim(layout, _claim("clm-2026-000002", status="proposed"))
    append_claim(layout, _claim("clm-2026-000002", status="superseded"))

    # Claim B: two verified revisions -> projects once (latest).
    append_claim(
        layout,
        _claim("clm-2026-000003", canonical_text="first verified revision text"),
    )
    append_claim(
        layout,
        _claim("clm-2026-000003", canonical_text="second verified revision text"),
    )

    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_ledger(layout, store)

    verified = store.query('?[id] := *claim{id, status}, status == "verified"')
    assert verified == [["clm-2026-000003"]]

    # The non-verified terminal claim is absent entirely.
    all_ids = sorted(r[0] for r in store.query("?[id] := *claim{id}"))
    assert all_ids == ["clm-2026-000003"]

    # Latest revision won the upsert.
    text = store.query("?[canonical_text] := *claim{canonical_text}")
    assert text == [["second verified revision text"]]


def test_span_id_is_stable_and_unique(tmp_path: Path) -> None:
    root = init_workspace(tmp_path / "ws")
    layout = WorkspaceLayout(root)
    append_claim(
        layout,
        _claim(
            "clm-2026-000004",
            source_spans=[
                {"doc_id": "doc-1", "locator_text": "first locator text here"},
                {"doc_id": "doc-2", "locator_text": "second locator text here"},
            ],
        ),
    )

    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_ledger(layout, store)

    ids = sorted(r[0] for r in store.query("?[id] := *source_span{id}"))
    assert len(ids) == 2
    assert len(set(ids)) == 2  # distinct minted ids

    claim_ids = {r[0] for r in store.query("?[claim_id] := *source_span{claim_id}")}
    assert claim_ids == {"clm-2026-000004"}
