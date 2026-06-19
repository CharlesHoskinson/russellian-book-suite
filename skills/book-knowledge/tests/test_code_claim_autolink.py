"""Tests for deterministic code-claim autolinking (REQ-KG-035..040)."""
from __future__ import annotations

import json
from pathlib import Path

import edn_format
import pytest

pytestmark = pytest.mark.windows_canary

from scripts.code_claim_autolink import (
    canonical_autolink_result,
    materialize_code_claim_links,
)
from scripts.cozo_store import CozoStore
from scripts.ledger import append_claim
from scripts.project_ledger_cozo import project_ledger
from scripts.workspace import WorkspaceLayout, init_workspace

SCHEMA = Path(__file__).resolve().parents[1] / "assets" / "kg-schema.edn"
GOLDEN = Path(__file__).resolve().parent / "golden" / "kg" / "code_claim_autolink.json"


def _workspace(tmp_path: Path) -> WorkspaceLayout:
    return WorkspaceLayout(init_workspace(tmp_path / "book"))


def _claim(
    num: int,
    text: str,
    *,
    source_file: str = "docs/source.md",
) -> dict:
    return {
        "claim_id": f"clm-2026-{num:06d}",
        "canonical_text": text,
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.8,
        "source_spans": [
            {"doc_id": source_file, "locator_text": f"source locator {num}"}
        ],
        "created_at": "2026-06-18T00:00:00+00:00",
    }


def _store(layout: WorkspaceLayout) -> CozoStore:
    store = CozoStore.in_memory(SCHEMA)
    project_ledger(layout, store)
    return store


def _load_code_graph(store: CozoStore, *, ambiguous: bool = False) -> None:
    nodes = [
        {
            "id": "mod-evictor",
            "label": "evictor.py",
            "source_file": "src/evictor.py",
            "community": "core",
        },
        {"id": "cls-evictor", "label": "Evictor", "source_file": "src/evictor.py"},
        {
            "id": "fn-rebalance",
            "label": "Evictor.rebalance",
            "source_file": "src/evictor.py",
        },
        {
            "id": "fn-no-trail",
            "label": "NoTrail.symbol",
            "source_file": "src/no_trail.py",
        },
    ]
    if ambiguous:
        nodes.extend(
            [
                {"id": "cache-a", "label": "Cache.flush", "source_file": "src/a.py"},
                {"id": "cache-b", "label": "Cache.flush", "source_file": "src/b.py"},
            ]
        )
    store.load("code-node", nodes)
    edges = [
        {
            "id": "edge-mod-class",
            "source_id": "mod-evictor",
            "target_id": "cls-evictor",
            "relationship": "contains",
        },
        {
            "id": "edge-class-fn",
            "source_id": "cls-evictor",
            "target_id": "fn-rebalance",
            "relationship": "uses",
        },
    ]
    if ambiguous:
        edges.extend(
            [
                {
                    "id": "edge-cache-a",
                    "source_id": "mod-evictor",
                    "target_id": "cache-a",
                    "relationship": "contains",
                },
                {
                    "id": "edge-cache-b",
                    "source_id": "mod-evictor",
                    "target_id": "cache-b",
                    "relationship": "uses",
                },
            ]
        )
    store.load("code-edge", edges)


def _links(store: CozoStore) -> list[dict]:
    rows = store.query(
        "?[id, code_id, claim_id, kind] := "
        "*code_claim_link{id, code_id, claim_id, kind}"
    )
    return [
        {"id": row[0], "code_id": row[1], "claim_id": row[2], "kind": row[3]}
        for row in sorted(rows)
    ]


def _evidence(store: CozoStore) -> list[dict]:
    rows = store.query(
        "?[id, code_id, claim_id, kind, score, witness, provenance, promoted] := "
        "*link_evidence{id, code_id, claim_id, kind, score, witness, provenance, promoted}"
    )
    return [
        {
            "id": row[0],
            "code_id": row[1],
            "claim_id": row[2],
            "kind": row[3],
            "score": row[4],
            "witness": row[5],
            "provenance": row[6],
            "promoted": row[7],
        }
        for row in sorted(rows)
    ]


def test_schema_declares_link_evidence(tmp_path: Path) -> None:
    """REQ-KG-035: schema declares evidence and canonical links have evidence."""
    schema = edn_format.loads(SCHEMA.read_text(encoding="utf-8"))
    entities = schema[edn_format.Keyword("entities")]
    evidence = entities[edn_format.Keyword("link-evidence")]
    attrs = {attr.name for attr in evidence[edn_format.Keyword("attrs")]}
    assert {"kind", "score", "witness", "provenance"} <= attrs
    assert "kind" in {
        attr.name
        for attr in entities[edn_format.Keyword("code-claim-link")][
            edn_format.Keyword("attrs")
        ]
    }

    layout = _workspace(tmp_path)
    append_claim(
        layout,
        _claim(1, "The source file anchors this claim.", source_file="src/evictor.py"),
    )
    before = layout.ledger.read_bytes()
    store = _store(layout)
    _load_code_graph(store)
    materialize_code_claim_links(store)

    evidence_pairs = {(row["code_id"], row["claim_id"]) for row in _evidence(store)}
    assert {
        (row["code_id"], row["claim_id"])
        for row in _links(store)
    } <= evidence_pairs
    assert layout.ledger.read_bytes() == before


def test_file_path_link_materialized(tmp_path: Path) -> None:
    """REQ-KG-036: exact source-file to module-path match promotes file-path link."""
    layout = _workspace(tmp_path)
    append_claim(
        layout,
        _claim(1, "The source file anchors this claim.", source_file="src/evictor.py"),
    )
    store = _store(layout)
    _load_code_graph(store)

    result = materialize_code_claim_links(store)

    assert {
        (row["code_id"], row["claim_id"], row["kind"])
        for row in result["canonical_links"]
    } == {("mod-evictor", "clm-2026-000001", "file-path")}
    evidence = result["link_evidence"]
    assert evidence == [
        {
            "id": "ev:file-path:mod-evictor:clm-2026-000001",
            "code_id": "mod-evictor",
            "claim_id": "clm-2026-000001",
            "kind": "file-path",
            "score": 1.0,
            "witness": "src/evictor.py",
            "provenance": "deterministic:file-path",
            "promoted": True,
        }
    ]


def test_exact_symbol_link_materialized(tmp_path: Path) -> None:
    """REQ-KG-037: exact symbol with CONTAINS/USES trail promotes canonical link."""
    layout = _workspace(tmp_path)
    append_claim(
        layout,
        _claim(1, "The claim cites `Evictor.rebalance` directly."),
    )
    store = _store(layout)
    _load_code_graph(store)

    result = materialize_code_claim_links(store)

    assert {
        (row["code_id"], row["claim_id"], row["kind"])
        for row in result["canonical_links"]
    } == {("fn-rebalance", "clm-2026-000001", "exact-symbol")}
    row = result["link_evidence"][0]
    assert row["kind"] == "exact-symbol"
    witness = json.loads(row["witness"])
    assert witness == {
        "symbol": "Evictor.rebalance",
        "trail": [
            {"source": "mod-evictor", "relationship": "contains", "target": "cls-evictor"},
            {"source": "cls-evictor", "relationship": "uses", "target": "fn-rebalance"},
        ],
    }


def test_only_deterministic_canonical(tmp_path: Path) -> None:
    """REQ-KG-038: no-trail symbol candidate remains evidence-only."""
    layout = _workspace(tmp_path)
    append_claim(
        layout,
        _claim(
            1,
            "The source file anchors this claim; `NoTrail.symbol` is only a weak candidate.",
            source_file="src/evictor.py",
        ),
    )
    store = _store(layout)
    _load_code_graph(store)

    result = materialize_code_claim_links(store)

    assert {
        (row["code_id"], row["claim_id"], row["kind"])
        for row in result["canonical_links"]
    } == {("mod-evictor", "clm-2026-000001", "file-path")}
    no_trail = [
        row for row in result["link_evidence"]
        if row["code_id"] == "fn-no-trail"
    ]
    assert len(no_trail) == 1
    assert no_trail[0]["kind"] == "exact-symbol"
    assert no_trail[0]["score"] == 0.5
    assert no_trail[0]["promoted"] is False


def test_linker_deterministic(tmp_path: Path) -> None:
    """REQ-KG-039: two runs are result-set-equal and match the frozen golden."""
    layout = _workspace(tmp_path)
    append_claim(
        layout,
        _claim(
            1,
            "The source file anchors this claim and `Evictor.rebalance` is named.",
            source_file="src/evictor.py",
        ),
    )
    store_a = _store(layout)
    store_b = _store(layout)
    _load_code_graph(store_a)
    _load_code_graph(store_b)

    first = canonical_autolink_result(materialize_code_claim_links(store_a))
    second = canonical_autolink_result(materialize_code_claim_links(store_b))

    assert first == second
    assert json.loads(first) == json.loads(GOLDEN.read_text(encoding="utf-8"))


def test_ambiguous_mention_not_promoted(tmp_path: Path) -> None:
    """REQ-KG-040: ambiguous exact mentions produce evidence-only candidates."""
    layout = _workspace(tmp_path)
    append_claim(layout, _claim(1, "The claim cites `Cache.flush` directly."))
    store = _store(layout)
    _load_code_graph(store, ambiguous=True)

    result = materialize_code_claim_links(store)

    assert result["canonical_links"] == []
    candidates = [
        row for row in result["link_evidence"]
        if row["claim_id"] == "clm-2026-000001"
    ]
    assert {
        (row["code_id"], row["kind"], row["promoted"])
        for row in candidates
    } == {
        ("cache-a", "exact-symbol", False),
        ("cache-b", "exact-symbol", False),
    }
