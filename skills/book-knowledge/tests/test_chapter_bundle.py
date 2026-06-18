"""Tests for chapter retrieval bundles (REQ-CHAP-001..008)."""
from __future__ import annotations

import json
from pathlib import Path

import edn_format

from scripts.cozo_store import CozoStore
from scripts.counter_claims import append_counter_claim
from scripts.ledger import append_claim
from scripts.project_chapter_bundle import (
    bundle_payload_canonical,
    chapter_uri,
    materialize_chapter_bundle,
    project_chapter_bundle,
    validate_bundle_payload,
)
from scripts.workspace import WorkspaceLayout, init_workspace

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "assets" / "kg-schema.edn"
GOLDEN_PATH = (
    Path(__file__).resolve().parent / "golden" / "kg" / "chapter_bundle_ch-01.json"
)


def _claim(
    claim_id: str,
    *,
    confidence: float,
    load_bearing: bool,
    source_spans: list[dict] | None = None,
    supports_chapters: list[str] | None = None,
) -> dict:
    return {
        "claim_id": claim_id,
        "canonical_text": f"{claim_id} supports the chapter argument",
        "status": "verified",
        "claim_type": "fact",
        "confidence": confidence,
        "load_bearing": load_bearing,
        "source_spans": source_spans
        if source_spans is not None
        else [{"doc_id": f"doc-{claim_id[-1]}", "locator_text": f"locator {claim_id}"}],
        "supports_chapters": supports_chapters or ["ch-01"],
        "created_at": "2026-06-17T00:00:00+00:00",
    }


def _counter_claim(
    cc_id: str,
    target_claim_id: str,
    status: str,
    *,
    created_at: str = "2026-06-17T01:00:00+00:00",
) -> dict:
    return {
        "id": cc_id,
        "target_claim_id": target_claim_id,
        "text": f"Counter claim {cc_id} challenges the target claim.",
        "disagreement_vector": "scope",
        "status": status,
        "provenance": {
            "generator": "fixture",
            "prompt_sha256": "0" * 64,
        },
        "created_at": created_at,
    }


def _store_with_fixture_graph(tmp_path: Path) -> tuple[WorkspaceLayout, CozoStore]:
    root = init_workspace(tmp_path / "book")
    layout = WorkspaceLayout(root)
    append_claim(
        layout,
        _claim(
            "clm-2026-000001",
            confidence=0.91,
            load_bearing=True,
            source_spans=[
                {"doc_id": "doc-a", "locator_text": "alpha locator"},
                {"doc_id": "doc-b", "locator_text": "beta locator"},
            ],
        ),
    )
    append_claim(
        layout,
        _claim("clm-2026-000002", confidence=0.84, load_bearing=True),
    )
    append_claim(
        layout,
        _claim("clm-2026-000003", confidence=0.67, load_bearing=False),
    )

    append_counter_claim(
        layout.root,
        _counter_claim("cc-2026-aaaaaa", "clm-2026-000001", "open"),
    )
    append_counter_claim(
        layout.root,
        _counter_claim("cc-2026-bbbbbb", "clm-2026-000002", "open"),
    )
    append_counter_claim(
        layout.root,
        _counter_claim("cc-2026-bbbbbb", "clm-2026-000002", "addressed"),
    )
    append_counter_claim(
        layout.root,
        _counter_claim("cc-2026-cccccc", "clm-2026-000001", "open"),
    )
    append_counter_claim(
        layout.root,
        _counter_claim("cc-2026-cccccc", "clm-2026-000001", "dismissed"),
    )

    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    store.load(
        "community",
        [
            {"id": "comm-alpha", "members": "code-a code-b"},
            {"id": "comm-beta", "members": "code-c"},
        ],
    )
    store.load(
        "code-node",
        [
            {"id": "code-a", "label": "module.alpha", "rank": 0.9, "community": "comm-alpha"},
            {"id": "code-b", "label": "module.beta", "rank": 0.8, "community": "comm-alpha"},
            {"id": "code-c", "label": "module.gamma", "rank": 0.7, "community": "comm-beta"},
        ],
    )
    store.load(
        "code-claim-link",
        [
            {"id": "code-a\x1fclm-2026-000001", "code_id": "code-a", "claim_id": "clm-2026-000001"},
            {"id": "code-b\x1fclm-2026-000002", "code_id": "code-b", "claim_id": "clm-2026-000002"},
            {"id": "code-c\x1fclm-2026-000001", "code_id": "code-c", "claim_id": "clm-2026-000001"},
        ],
    )
    return layout, store


def _payload(layout: WorkspaceLayout, store: CozoStore) -> dict:
    return project_chapter_bundle(layout, "ch-01", store=store)["payload"]


def test_one_bundle_per_chapter(tmp_path: Path) -> None:
    """REQ-CHAP-001: one bundle row per chapter and the ledger stays unchanged."""
    layout, store = _store_with_fixture_graph(tmp_path)
    before = layout.ledger.read_bytes()

    project_chapter_bundle(layout, "ch-01", store=store)
    project_chapter_bundle(layout, "ch-01", store=store)

    rows = store.query(
        '?[id, chapter_id] := *chapter_retrieval_bundle{id, chapter_id}, '
        'chapter_id == "ch-01"'
    )
    assert rows == [["bundle:ch-01", "ch-01"]]
    assert layout.ledger.read_bytes() == before


def test_bundle_payload_sections(tmp_path: Path) -> None:
    """REQ-CHAP-002: bundle carries the four required payload sections."""
    layout, store = _store_with_fixture_graph(tmp_path)
    payload = _payload(layout, store)

    assert payload["dominant-communities"]
    assert payload["dominant-communities"][0]["community-id"] == "comm-alpha"
    assert [c["claim-id"] for c in payload["load-bearing-claims"]] == [
        "clm-2026-000001",
        "clm-2026-000002",
    ]
    assert payload["unresolved-rebuttals"]
    assert payload["source-span-anchors"]


def test_bundle_is_structured(tmp_path: Path) -> None:
    """REQ-CHAP-003: bundle is schema-valid JSON/EDN keyed by sections."""
    layout, store = _store_with_fixture_graph(tmp_path)
    row = project_chapter_bundle(layout, "ch-01", store=store)

    decoded_json = json.loads(row["payload_json"])
    assert decoded_json == row["payload"]
    validate_bundle_payload(decoded_json)
    decoded_edn = edn_format.loads(row["payload_edn"])
    assert decoded_edn is not None
    assert "passages" not in decoded_json
    for key in (
        "dominant-communities",
        "load-bearing-claims",
        "unresolved-rebuttals",
        "source-span-anchors",
    ):
        assert key in decoded_json


def test_open_rebuttal_surfaced(tmp_path: Path) -> None:
    """REQ-CHAP-004: latest open counter-claims are unresolved rebuttals."""
    layout, store = _store_with_fixture_graph(tmp_path)
    payload = _payload(layout, store)

    assert payload["unresolved-rebuttals"] == [
        {
            "counter-claim-id": "cc-2026-aaaaaa",
            "target-claim-id": "clm-2026-000001",
            "status": "open",
            "created-at": "2026-06-17T01:00:00+00:00",
        }
    ]


def test_projection_deterministic(tmp_path: Path) -> None:
    """REQ-CHAP-005: two runs on one snapshot equal the frozen golden."""
    layout, store = _store_with_fixture_graph(tmp_path)

    first = bundle_payload_canonical(_payload(layout, store))
    second = bundle_payload_canonical(_payload(layout, store))
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert first == second
    assert first == golden


def test_minimal_span_cover(tmp_path: Path) -> None:
    """REQ-CHAP-006: anchors cover each selected claim and no removable span remains."""
    layout, store = _store_with_fixture_graph(tmp_path)
    payload = _payload(layout, store)
    selected = {c["claim-id"] for c in payload["load-bearing-claims"]}
    anchors = payload["source-span-anchors"]

    assert {a["claim-id"] for a in anchors} == selected
    for anchor in anchors:
        remaining = [a for a in anchors if a != anchor]
        assert {a["claim-id"] for a in remaining} != selected

    span_rows = store.query(
        '?[id, claim_id] := *source_span{id, claim_id}, '
        'claim_id == "clm-2026-000001"'
    )
    expected_tie_break = min(row[0] for row in span_rows)
    actual = [
        a["span-id"]
        for a in anchors
        if a["claim-id"] == "clm-2026-000001"
    ][0]
    assert actual == expected_tie_break


def test_code_links_included(tmp_path: Path) -> None:
    """REQ-CHAP-007: code links are included only where applicable."""
    layout, store = _store_with_fixture_graph(tmp_path)
    payload = _payload(layout, store)

    assert payload["code-links"] == {
        "clm-2026-000001": [{"code-id": "code-a"}, {"code-id": "code-c"}],
        "clm-2026-000002": [{"code-id": "code-b"}],
    }

    no_code_root = init_workspace(tmp_path / "no-code")
    no_code_layout = WorkspaceLayout(no_code_root)
    append_claim(
        no_code_layout,
        _claim("clm-2026-000004", confidence=0.72, load_bearing=True),
    )
    no_code_payload = project_chapter_bundle(no_code_layout, "ch-01")["payload"]
    assert "code-links" not in no_code_payload


def test_unanchored_load_bearing_flagged(tmp_path: Path) -> None:
    """REQ-CHAP-008: load-bearing claims without spans are flagged."""
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    uri = chapter_uri("ch-02")
    store.load(
        "claim",
        [
            {
                "id": "clm-2026-000009",
                "canonical_text": "unanchored claim text",
                "status": "verified",
                "claim_type": "fact",
                "confidence": 0.7,
                "load_bearing": True,
            }
        ],
    )
    store.load("chapter", [{"id": uri}])
    store.load(
        "claim-chapter",
        [
            {
                "id": f"clm-2026-000009\x1f{uri}",
                "claim_id": "clm-2026-000009",
                "chapter": uri,
            }
        ],
    )

    payload = materialize_chapter_bundle(store, "ch-02")["payload"]

    assert payload["source-span-anchors"] == []
    assert payload["flags"] == {
        "unanchored-load-bearing": [
            {"claim-id": "clm-2026-000009", "reason": "no-source-span"}
        ]
    }
