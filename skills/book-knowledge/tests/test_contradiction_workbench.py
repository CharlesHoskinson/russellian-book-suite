"""Tests for the S4 normalized contradiction workbench (REQ-KG-021..027)."""
from __future__ import annotations

import json
from pathlib import Path

import edn_format

from scripts.contradiction_workbench import (
    NLIUnavailable,
    canonical_workbench_result,
    run_contradiction_workbench,
    run_symbolic_checks,
)
from scripts.cozo_store import CozoStore
from scripts.ledger import append_claim
from scripts.project_ledger_cozo import project_ledger
from scripts.workspace import WorkspaceLayout, init_workspace

SCHEMA = Path(__file__).resolve().parents[1] / "assets" / "kg-schema.edn"


def _workspace(tmp_path: Path) -> WorkspaceLayout:
    return WorkspaceLayout(init_workspace(tmp_path / "book"))


def _claim(
    num: int,
    text: str,
    *,
    status: str = "verified",
    supersedes: str | None = None,
    conflicts_with: list[str] | None = None,
) -> dict:
    row = {
        "claim_id": f"clm-2026-{num:06d}",
        "canonical_text": text,
        "status": status,
        "claim_type": "fact",
        "confidence": 0.9,
        "source_spans": [{"doc_id": f"doc-{num}", "locator_text": f"locator {num}"}],
        "created_at": "2026-06-18T00:00:00+00:00",
    }
    if supersedes is not None:
        row["supersedes"] = supersedes
    if conflicts_with is not None:
        row["conflicts_with"] = conflicts_with
    return row


def _store(layout: WorkspaceLayout) -> CozoStore:
    store = CozoStore.in_memory(SCHEMA)
    project_ledger(layout, store)
    return store


def _alerts_by_rule(result: dict, rule: str) -> list[dict]:
    return [
        row for row in result["contradiction_alerts"]
        if row.get("rule") == rule
    ]


def test_schema_declares_helper_relations(tmp_path: Path) -> None:
    """REQ-KG-021: schema declares and projector emits normalized helper rows."""
    schema = edn_format.loads(SCHEMA.read_text(encoding="utf-8"))
    entities = schema[edn_format.Keyword("entities")]
    for name in (
        "claim-quantity",
        "claim-unit",
        "claim-time-interval",
        "claim-normal-form",
    ):
        body = entities[edn_format.Keyword(name)]
        assert body[edn_format.Keyword("attrs")]

    layout = _workspace(tmp_path)
    append_claim(
        layout,
        _claim(
            1,
            "route length is 30 km from 1910 to 1915 requires overlap",
        ),
    )
    before = layout.ledger.read_bytes()
    store = _store(layout)

    assert store.query("?[claim_id] := *claim_quantity{claim_id}") == [["clm-2026-000001"]]
    assert store.query("?[claim_id] := *claim_unit{claim_id}") == [["clm-2026-000001"]]
    assert store.query("?[claim_id] := *claim_time_interval{claim_id}") == [["clm-2026-000001"]]
    assert store.query("?[claim_id] := *claim_normal_form{claim_id}") == [["clm-2026-000001"]]
    assert layout.ledger.read_bytes() == before


def test_quantity_clash_after_unit_normalization(tmp_path: Path) -> None:
    """REQ-KG-022: incompatible normalized quantities clash; equal conversions do not."""
    layout = _workspace(tmp_path)
    append_claim(layout, _claim(1, "route length is 30 km"))
    append_claim(layout, _claim(2, "route length is 300 km"))
    append_claim(layout, _claim(3, "corridor length is 30 km"))
    append_claim(layout, _claim(4, "corridor length is 30000 m"))
    append_claim(layout, _claim(5, "trail length is 30 km"))
    append_claim(layout, _claim(6, "trail length is 30000000 cm"))

    result = run_symbolic_checks(_store(layout), layout=layout)
    clashes = _alerts_by_rule(result, "quantity-clash")

    assert {
        tuple(row["claim_ids"])
        for row in clashes
    } == {
        ("clm-2026-000001", "clm-2026-000002"),
        ("clm-2026-000005", "clm-2026-000006"),
    }
    assert ("clm-2026-000003", "clm-2026-000004") not in {
        tuple(row["claim_ids"]) for row in clashes
    }


def test_interval_inconsistency_flagged(tmp_path: Path) -> None:
    """REQ-KG-023: interval requirements flag only violated temporal relations."""
    layout = _workspace(tmp_path)
    append_claim(layout, _claim(1, "site occupation active from 1910 to 1915 requires overlap"))
    append_claim(layout, _claim(2, "site occupation active from 1920 to 1925 requires overlap"))
    append_claim(layout, _claim(3, "archive period active from 1910 to 1920 requires overlap"))
    append_claim(layout, _claim(4, "archive period active from 1915 to 1925 requires overlap"))
    append_claim(layout, _claim(5, "permit window active from 1910 to 1915 requires disjoint"))
    append_claim(layout, _claim(6, "permit window active from 1912 to 1914 requires disjoint"))

    result = run_symbolic_checks(_store(layout), layout=layout)
    intervals = _alerts_by_rule(result, "interval-inconsistency")

    assert {
        tuple(row["claim_ids"])
        for row in intervals
    } == {
        ("clm-2026-000001", "clm-2026-000002"),
        ("clm-2026-000005", "clm-2026-000006"),
    }


def test_stale_or_invalid_supersession_flagged(tmp_path: Path) -> None:
    """REQ-KG-024: stale, missing, and cyclic supersession chains are flagged."""
    layout = _workspace(tmp_path)
    append_claim(layout, _claim(1, "old route length is 30 km"))
    append_claim(layout, _claim(2, "new route length is 31 km", supersedes="clm-2026-000001"))
    append_claim(layout, _claim(3, "retired estimate length is 10 km", status="superseded"))
    append_claim(layout, _claim(4, "replacement estimate length is 11 km", supersedes="clm-2026-000003"))
    append_claim(layout, _claim(5, "missing target length is 12 km", supersedes="clm-2026-999999"))
    append_claim(layout, _claim(6, "cycle one length is 13 km", supersedes="clm-2026-000007"))
    append_claim(layout, _claim(7, "cycle two length is 14 km", supersedes="clm-2026-000006"))

    result = run_symbolic_checks(_store(layout), layout=layout)
    stale = _alerts_by_rule(result, "supersession-stale")
    invalid = _alerts_by_rule(result, "supersession-invalid")

    assert {tuple(row["claim_ids"]) for row in stale} == {
        ("clm-2026-000002", "clm-2026-000001")
    }
    assert {
        (row["claim_ids"][0], row["evidence"]["kind"])
        for row in invalid
    } == {
        ("clm-2026-000005", "missing-target"),
        ("clm-2026-000006", "cycle"),
        ("clm-2026-000007", "cycle"),
    }
    assert all("clm-2026-000004" not in row["claim_ids"] for row in stale + invalid)


def test_symbolic_checks_deterministic(tmp_path: Path) -> None:
    """REQ-KG-025: symbolic checks are result-set-equal and do not mutate ledger."""
    layout = _workspace(tmp_path)
    append_claim(layout, _claim(1, "route length is 30 km"))
    append_claim(layout, _claim(2, "route length is 300 km"))
    append_claim(layout, _claim(3, "site occupation active from 1910 to 1915 requires overlap"))
    append_claim(layout, _claim(4, "site occupation active from 1920 to 1925 requires overlap"))
    before = layout.ledger.read_bytes()

    first = canonical_workbench_result(run_symbolic_checks(_store(layout), layout=layout))
    second = canonical_workbench_result(run_symbolic_checks(_store(layout), layout=layout))

    assert first == second
    assert layout.ledger.read_bytes() == before


def test_residue_routes_to_nli_seam(tmp_path: Path) -> None:
    """REQ-KG-026: only non-symbolic candidate pairs route to the injected seam."""
    layout = _workspace(tmp_path)
    append_claim(layout, _claim(1, "route length is 30 km", conflicts_with=["clm-2026-000002"]))
    append_claim(layout, _claim(2, "route length is 300 km"))
    append_claim(layout, _claim(3, "the archive is materially complete", conflicts_with=["clm-2026-000004"]))
    append_claim(layout, _claim(4, "the archive omits a material appendix"))
    calls: list[tuple[str, str]] = []

    def fake_nli(payload: dict) -> dict:
        calls.append((payload["left_claim_id"], payload["right_claim_id"]))
        return {"status": "contradiction", "confidence": 0.82}

    result = run_contradiction_workbench(layout, nli_call=fake_nli)

    assert calls == [("clm-2026-000003", "clm-2026-000004")]
    assert {
        tuple(row["claim_ids"])
        for row in _alerts_by_rule(result, "quantity-clash")
    } == {("clm-2026-000001", "clm-2026-000002")}
    assert result["residue"][0]["status"] == "contradiction"


def test_residue_unresolved_when_seam_down(tmp_path: Path) -> None:
    """REQ-KG-027: seam-down residue is marked unresolved, not dropped."""
    layout = _workspace(tmp_path)
    append_claim(layout, _claim(1, "route length is 30 km", conflicts_with=["clm-2026-000002"]))
    append_claim(layout, _claim(2, "route length is 300 km"))
    append_claim(layout, _claim(3, "the archive is materially complete", conflicts_with=["clm-2026-000004"]))
    append_claim(layout, _claim(4, "the archive omits a material appendix"))

    symbolic = run_symbolic_checks(_store(layout), layout=layout)

    def unavailable(payload: dict) -> dict:
        raise NLIUnavailable("offline")

    result = run_contradiction_workbench(layout, nli_call=unavailable)

    assert canonical_workbench_result(result["symbolic"]) == canonical_workbench_result(symbolic)
    assert result["residue"] == [
        {
            "claim_ids": ["clm-2026-000003", "clm-2026-000004"],
            "rule": "paraphrastic-residue",
            "status": "unresolved",
            "reason": "nli-unavailable",
        }
    ]
    assert json.dumps(result["contradiction_alerts"], sort_keys=True)
