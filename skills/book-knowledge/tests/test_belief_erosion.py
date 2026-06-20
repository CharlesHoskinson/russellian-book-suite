"""Tests for S5 effective-confidence materialization (REQ-KG-028..034)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

pytestmark = pytest.mark.windows_canary

from scripts.belief_graph import load_belief_graph, load_source_trust
from scripts.cozo_store import CozoStore
from scripts.counter_claims import append_counter_claim
from scripts.effective_confidence import (
    canonical_effective_confidence_rows,
    compute_why_provenance,
    materialize_effective_confidence,
)
from scripts.io_utils import latest_per, read_jsonl
from scripts.ledger import append_claim
from scripts.project_ledger_cozo import project_ledger
from scripts.propagate_belief import propagate
from scripts.workspace import WorkspaceLayout, init_workspace

SCHEMA = Path(__file__).resolve().parents[1] / "assets" / "kg-schema.edn"
AS_OF = "2026-06-18T00:00:00Z"


def _workspace(tmp_path: Path) -> WorkspaceLayout:
    return WorkspaceLayout(init_workspace(tmp_path / "book"))


def _claim(
    num: int,
    text: str,
    *,
    status: str = "verified",
    source: str | None = None,
    derived_from: list[str] | None = None,
    conflicts_with: list[str] | None = None,
    load_bearing: bool = False,
    created_at: str = "2026-06-10T00:00:00Z",
) -> dict:
    claim_id = f"clm-2026-{num:06d}"
    record = {
        "claim_id": claim_id,
        "canonical_text": text,
        "status": status,
        "claim_type": "fact",
        "confidence": 0.8,
        "source_spans": [
            {
                "doc_id": source or f"src-{num}",
                "locator_text": f"source locator text {num}",
            }
        ],
        "created_at": created_at,
    }
    if derived_from is not None:
        record["derived_from"] = derived_from
    if conflicts_with is not None:
        record["conflicts_with"] = conflicts_with
    if load_bearing:
        record["load_bearing"] = True
    return record


def _manifest(
    layout: WorkspaceLayout,
    doc_id: str,
    *,
    trust: float = 1.0,
    ingested_at: str = "2026-06-17T00:00:00Z",
) -> None:
    (layout.manifests / f"{doc_id}.json").write_text(
        json.dumps(
            {
                "doc_name": f"{doc_id}.md",
                "doc_id": doc_id,
                "source_kind": "markdown",
                "sha256": "0" * 64,
                "ingested_at": ingested_at,
                "node_count": 1,
                "trust": trust,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _counter_claim(
    layout: WorkspaceLayout,
    cc_id: str,
    target: str,
    *,
    status: str = "open",
) -> None:
    append_counter_claim(
        layout.root,
        {
            "id": cc_id,
            "target_claim_id": target,
            "text": "A rival account challenges the target claim.",
            "disagreement_vector": "scope",
            "status": status,
            "provenance": {"generator": "test", "prompt_sha256": "0" * 64},
            "created_at": "2026-06-12T00:00:00Z",
            "addressed_in_chapter": None,
        },
    )


def _store(layout: WorkspaceLayout) -> CozoStore:
    store = CozoStore.in_memory(SCHEMA)
    project_ledger(layout, store)
    return store


def _by_claim(rows: list[dict]) -> dict[str, dict]:
    return {row["claim_id"]: row for row in rows}


def test_effective_confidence_materialized(tmp_path: Path) -> None:
    """REQ-KG-028: materializes one queryable row per latest claim, read-only."""
    layout = _workspace(tmp_path)
    append_claim(layout, _claim(1, "First claim has a stable source.", source="src-a"))
    append_claim(layout, _claim(2, "Second claim has a stable source.", source="src-b"))
    append_claim(
        layout,
        _claim(
            2,
            "Second claim latest revision has the same id.",
            source="src-b",
            created_at="2026-06-11T00:00:00Z",
        ),
    )
    _manifest(layout, "src-a")
    _manifest(layout, "src-b")
    before = layout.ledger.read_bytes()

    store = _store(layout)
    rows = materialize_effective_confidence(layout, store, as_of=AS_OF)

    assert {row["claim_id"] for row in rows} == {
        "clm-2026-000001",
        "clm-2026-000002",
    }
    assert len(rows) == 2
    assert store.query(
        "?[claim_id, effective] := "
        "*effective_confidence{claim_id, effective}"
    )
    assert layout.ledger.read_bytes() == before


def test_erosion_reason_minimal(tmp_path: Path) -> None:
    """REQ-KG-029: a drop names only the responsible counter-claim and parent."""
    layout = _workspace(tmp_path)
    parent_id = "clm-2026-000001"
    child_id = "clm-2026-000002"
    append_claim(
        layout,
        _claim(1, "Weak parent claim has low status.", status="disputed", source="parent-src"),
    )
    append_claim(
        layout,
        _claim(
            2,
            "Child claim depends on the weak parent.",
            source="child-src",
            derived_from=[parent_id],
        ),
    )
    _manifest(layout, "parent-src")
    _manifest(layout, "child-src")
    _counter_claim(layout, "cc-2026-a00001", child_id)

    rows = _by_claim(materialize_effective_confidence(layout, _store(layout), as_of=AS_OF))

    assert rows[child_id]["effective"] < rows[child_id]["prior"]
    assert rows[child_id]["support_erosion_reason"] == [
        {"kind": "counter-claim", "id": "cc-2026-a00001", "status": "open"},
        {"kind": "weakened-parent", "claim_id": parent_id},
    ]
    assert rows[parent_id]["support_erosion_reason"] == []


def test_refreshed_source_conflict_erodes(tmp_path: Path) -> None:
    """REQ-KG-030: a fresh trusted conflicting source erodes and is named."""
    layout = _workspace(tmp_path)
    target_id = "clm-2026-000001"
    conflict_id = "clm-2026-000002"
    append_claim(
        layout,
        _claim(
            1,
            "Original supported claim from an older source.",
            source="support-src",
            created_at="2026-06-01T00:00:00Z",
        ),
    )
    append_claim(
        layout,
        _claim(
            2,
            "Refreshed source now introduces a trusted conflict.",
            source="refresh-src",
            conflicts_with=[target_id],
            created_at="2026-06-17T00:00:00Z",
        ),
    )
    _manifest(layout, "support-src", trust=1.0, ingested_at="2026-06-01T00:00:00Z")
    _manifest(layout, "refresh-src", trust=0.95, ingested_at="2026-06-17T00:00:00Z")

    rows = _by_claim(materialize_effective_confidence(layout, _store(layout), as_of=AS_OF))
    reason = rows[target_id]["support_erosion_reason"]

    assert rows[target_id]["effective"] < rows[target_id]["prior"]
    assert {
        "kind": "refreshed-source-conflict",
        "source_id": "refresh-src",
        "conflict_claim_id": conflict_id,
    } in reason


def test_why_provenance_on_demand(tmp_path: Path) -> None:
    """REQ-KG-031: provenance is bounded, cached, and only for flagged load-bearing."""
    layout = _workspace(tmp_path)
    before = layout.ledger.read_bytes()
    append_claim(layout, _claim(1, "Parent support exists.", source="parent-src"))
    append_claim(
        layout,
        _claim(
            2,
            "Load-bearing claim needs explanation.",
            source="child-src",
            derived_from=["clm-2026-000001"],
            load_bearing=True,
        ),
    )
    append_claim(layout, _claim(3, "Non load-bearing claim is not explained.", source="other-src"))
    before = layout.ledger.read_bytes()

    result = compute_why_provenance(
        layout,
        flagged_claim_ids={"clm-2026-000002", "clm-2026-000003"},
        bound=4,
    )

    assert set(result) == {"clm-2026-000002"}
    assert result["clm-2026-000002"]["truncated"] is False
    assert result["clm-2026-000002"]["witnesses"] == [
        {"kind": "parent-claim", "id": "clm-2026-000001"},
        {"kind": "source", "id": "child-src"},
    ]
    cache = layout.root / "claims" / "why-provenance.jsonl"
    assert len(read_jsonl(cache)) == 1
    assert layout.ledger.read_bytes() == before


def test_freshness_decay(tmp_path: Path) -> None:
    """REQ-KG-032: source age discounts trust under an explicit reference time."""
    layout = _workspace(tmp_path)
    append_claim(layout, _claim(1, "Old source supports this claim.", source="old-src"))
    append_claim(layout, _claim(2, "Fresh source supports this claim.", source="fresh-src"))
    _manifest(layout, "old-src", trust=1.0, ingested_at="2020-01-01T00:00:00Z")
    _manifest(layout, "fresh-src", trust=1.0, ingested_at="2026-06-17T00:00:00Z")

    trust = load_source_trust(layout.root, as_of=AS_OF)
    first = canonical_effective_confidence_rows(
        materialize_effective_confidence(layout, _store(layout), as_of=AS_OF)
    )
    second = canonical_effective_confidence_rows(
        materialize_effective_confidence(layout, _store(layout), as_of=AS_OF)
    )
    rows = _by_claim(json.loads(first))

    assert trust["old-src"] < trust["fresh-src"]
    assert rows["clm-2026-000001"]["effective"] < rows["clm-2026-000002"]["effective"]
    assert first == second


def test_effective_confidence_deterministic_reuses_engine(tmp_path: Path, monkeypatch) -> None:
    """REQ-KG-033: output is result-set-equal and uses propagate_belief.propagate."""
    layout = _workspace(tmp_path)
    append_claim(layout, _claim(1, "Engine-backed claim.", source="engine-src"))
    _manifest(layout, "engine-src", trust=0.8, ingested_at="2026-06-17T00:00:00Z")
    calls = {"count": 0}

    from scripts import effective_confidence as module

    real_propagate = module.propagate

    def counting_propagate(*args, **kwargs):
        calls["count"] += 1
        return real_propagate(*args, **kwargs)

    monkeypatch.setattr(module, "propagate", counting_propagate)

    first_rows = materialize_effective_confidence(layout, _store(layout), as_of=AS_OF)
    second_rows = materialize_effective_confidence(layout, _store(layout), as_of=AS_OF)

    trust = load_source_trust(layout.root, as_of=AS_OF)
    counter_claims = list(
        latest_per(read_jsonl(layout.root / "claims" / "counter-claims.jsonl"), "id").values()
    )
    expected = propagate(load_belief_graph(layout.root), trust, counter_claims)

    assert calls["count"] == 2
    assert canonical_effective_confidence_rows(first_rows) == canonical_effective_confidence_rows(second_rows)
    assert math.isclose(
        _by_claim(first_rows)["clm-2026-000001"]["effective"],
        expected["clm-2026-000001"],
        rel_tol=1e-6,
    )


def test_why_provenance_truncates_at_bound(tmp_path: Path) -> None:
    """REQ-KG-034: oversized witnesses return a bounded, marked-truncated set."""
    layout = _workspace(tmp_path)
    parents = []
    for idx in range(1, 5):
        cid = f"clm-2026-{idx:06d}"
        parents.append(cid)
        append_claim(layout, _claim(idx, f"Parent support {idx}.", source=f"parent-{idx}"))
    append_claim(
        layout,
        _claim(
            5,
            "Load-bearing claim with too many direct witnesses.",
            source="child-src",
            derived_from=parents,
            load_bearing=True,
        ),
    )

    result = compute_why_provenance(
        layout,
        flagged_claim_ids={"clm-2026-000005"},
        bound=2,
    )

    row = result["clm-2026-000005"]
    assert row["truncated"] is True
    assert row["witnesses"] == [
        {"kind": "parent-claim", "id": "clm-2026-000001"},
        {"kind": "parent-claim", "id": "clm-2026-000002"},
    ]
