"""Tests for the ledger->cozo projector (REQ-KG-004).

`project_ledger` loads every latest-per-id NON-SUPERSEDED claim and its
source-spans from the append-only ledger into the Cozo store's `claim` and
`source_span` relations, without touching the ledger file. This mirrors
`project_graph`'s RDF emit, which skips only `superseded`, so the Cozo node set
equals the RDF node set and the status-agnostic competency queries see the same
claims under both backends.
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


def test_projects_latest_nonsuperseded_claims(tmp_path: Path) -> None:
    """REQ-KG-004: project latest-per-id non-superseded claims.

    Mirrors project_graph's filter exactly: a verified claim and a non-verified
    non-superseded claim (proposed) are BOTH projected; a superseded claim is
    NOT; two revisions of the same id collapse to the latest. Each projected row
    carries its status, and the ledger is left byte-for-byte untouched.
    """
    root = init_workspace(tmp_path / "ws")
    layout = WorkspaceLayout(root)

    # Verified claim -> projected.
    append_claim(layout, _claim("clm-2026-000001", status="verified"))
    # Non-verified, non-superseded claim (proposed) -> ALSO projected.
    append_claim(layout, _claim("clm-2026-000005", status="proposed"))
    # Superseded claim -> NOT projected.
    append_claim(layout, _claim("clm-2026-000006", status="proposed"))
    append_claim(layout, _claim("clm-2026-000006", status="superseded"))
    # Two revisions collapse to the latest tip.
    append_claim(
        layout,
        _claim("clm-2026-000007", canonical_text="first revision text here"),
    )
    append_claim(
        layout,
        _claim("clm-2026-000007", canonical_text="second revision text here"),
    )

    before = layout.ledger.read_text(encoding="utf-8")

    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_ledger(layout, store)

    # The verified and the proposed claim are both present; superseded is gone.
    all_ids = sorted(r[0] for r in store.query("?[id] := *claim{id}"))
    assert all_ids == [
        "clm-2026-000001",
        "clm-2026-000005",
        "clm-2026-000007",
    ]

    # Each row carries its status (status column projected).
    by_status = {
        r[0]: r[1] for r in store.query("?[id, status] := *claim{id, status}")
    }
    assert by_status["clm-2026-000001"] == "verified"
    assert by_status["clm-2026-000005"] == "proposed"

    # Two revisions collapsed to the latest tip.
    text = store.query(
        '?[canonical_text] := *claim{id, canonical_text}, '
        'id == "clm-2026-000007"'
    )
    assert text == [["second revision text here"]]

    # Spans came across for the projected claims (back-ref to owning claim id).
    span_claim_ids = sorted(
        {r[0] for r in store.query("?[claim_id] := *source_span{claim_id}")}
    )
    assert span_claim_ids == [
        "clm-2026-000001",
        "clm-2026-000005",
        "clm-2026-000007",
    ]

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


def test_superseded_dropped_but_other_terminals_kept(tmp_path: Path) -> None:
    """Only `superseded` is dropped; the other terminal state `refuted` stays.

    project_graph skips solely `superseded`, so the projector must keep `refuted`
    (and every other non-superseded status) to hold the same node set.
    """
    root = init_workspace(tmp_path / "ws")
    layout = WorkspaceLayout(root)

    # Claim A: proposed then flipped to superseded (terminal) -> dropped.
    append_claim(layout, _claim("clm-2026-000002", status="proposed"))
    append_claim(layout, _claim("clm-2026-000002", status="superseded"))

    # Claim B: disputed then flipped to refuted (terminal, NOT superseded) -> kept.
    append_claim(layout, _claim("clm-2026-000008", status="disputed"))
    append_claim(layout, _claim("clm-2026-000008", status="refuted"))

    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_ledger(layout, store)

    # Superseded gone; refuted present.
    all_ids = sorted(r[0] for r in store.query("?[id] := *claim{id}"))
    assert all_ids == ["clm-2026-000008"]

    refuted = store.query('?[id] := *claim{id, status}, status == "refuted"')
    assert refuted == [["clm-2026-000008"]]


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
