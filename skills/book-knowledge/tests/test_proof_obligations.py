"""Tests for proof-obligation entities and checker dispatch (REQ-PROOF-001..004,007..008)."""
from __future__ import annotations

import json
from pathlib import Path

import edn_format
import pytest

pytestmark = pytest.mark.windows_canary

from scripts.cozo_store import CozoStore
from scripts.ledger import append_claim
from scripts.project_ledger_cozo import project_ledger
from scripts.proof_obligations import (
    ProofObligationValidationError,
    check_scientific_claim,
    open_pending_obligation,
    read_proof_obligations,
    read_verification_artifacts,
    run_checker,
    validate_proof_obligation,
)
from scripts.workspace import WorkspaceLayout, init_workspace

SCHEMA = Path(__file__).resolve().parents[1] / "assets" / "kg-schema.edn"


def _workspace(tmp_path: Path) -> WorkspaceLayout:
    return WorkspaceLayout(init_workspace(tmp_path / "book"))


def _claim(claim_id: str = "clm-2026-000001", text: str = "For all x, x equals x.") -> dict:
    return {
        "claim_id": claim_id,
        "canonical_text": text,
        "status": "verified",
        "claim_type": "result",
        "confidence": 0.9,
        "source_spans": [{"doc_id": "proof.md", "locator_text": "proof locator text"}],
        "created_at": "2026-06-18T00:00:00+00:00",
    }


def test_schema_declares_obligation_entities(tmp_path: Path) -> None:
    """REQ-PROOF-001: schema declares entities and validator rejects missing fields."""
    schema = edn_format.loads(SCHEMA.read_text(encoding="utf-8"))
    entities = schema[edn_format.Keyword("entities")]
    for name in ("proof-obligation", "verification-artifact", "requires-proof"):
        assert edn_format.Keyword(name) in entities
    obligation_attrs = {
        attr.name
        for attr in entities[edn_format.Keyword("proof-obligation")][
            edn_format.Keyword("attrs")
        ]
    }
    assert {
        "statement",
        "linked-claim",
        "checker-kind",
        "status",
        "assumptions",
        "artifact-path",
        "countermodel-path",
        "checked-at",
        "normal-form",
    } <= obligation_attrs

    with pytest.raises(ProofObligationValidationError, match="checker"):
        validate_proof_obligation({"id": "obl-1", "status": "pending"})
    with pytest.raises(ProofObligationValidationError, match="status"):
        validate_proof_obligation({"id": "obl-1", "checker_kind": "z3"})
    with pytest.raises(ProofObligationValidationError, match="artifact_path"):
        validate_proof_obligation(
            {
                "id": "obl-1",
                "statement": "x equals x",
                "linked_claim": "clm-2026-000001",
                "checker_kind": "z3",
                "status": "discharged",
            }
        )
    with pytest.raises(ProofObligationValidationError, match="countermodel_path"):
        validate_proof_obligation(
            {
                "id": "obl-1",
                "statement": "x equals x",
                "linked_claim": "clm-2026-000001",
                "checker_kind": "z3",
                "status": "refuted",
            }
        )

    store = CozoStore.in_memory(SCHEMA)
    assert "proof_obligation" in store.relations()
    assert "verification_artifact" in store.relations()
    assert "requires_proof" in store.relations()


def test_requires_proof_opens_pending_obligation(tmp_path: Path) -> None:
    """REQ-PROOF-002: requiring proof opens exactly one pending obligation."""
    layout = _workspace(tmp_path)
    append_claim(layout, _claim())
    ledger_before = layout.ledger.read_bytes()

    first = open_pending_obligation(
        layout,
        claim_id="clm-2026-000001",
        statement="For all x, x equals x.",
        checker_kind="z3",
        normal_form="forall x. x == x",
    )
    second = open_pending_obligation(
        layout,
        claim_id="clm-2026-000001",
        statement="For all x, x equals x.",
        checker_kind="z3",
        normal_form="forall x. x == x",
    )

    obligations = read_proof_obligations(layout)
    assert layout.ledger.read_bytes() == ledger_before
    assert first["id"] == second["id"]
    assert len(obligations) == 1
    assert obligations[0]["linked_claim"] == "clm-2026-000001"
    assert obligations[0]["checker_kind"] == "z3"
    assert obligations[0]["status"] == "pending"


def test_discharge_records_artifact(tmp_path: Path) -> None:
    """REQ-PROOF-003: proved checker result records artifact and discharges."""
    layout = _workspace(tmp_path)
    append_claim(layout, _claim())
    ledger_before = layout.ledger.read_bytes()
    obligation = open_pending_obligation(
        layout,
        claim_id="clm-2026-000001",
        statement="For all x, x equals x.",
        checker_kind="z3",
        normal_form="forall x. x == x",
    )

    def checker(record: dict) -> dict:
        return {"status": "proved", "artifact": {"solver": "stub", "result": "sat"}}

    result = run_checker(
        layout,
        obligation["id"],
        checker_dispatch={"z3": checker},
        checked_at="2026-06-18T00:00:00Z",
    )

    assert result["status"] == "discharged"
    assert layout.ledger.read_bytes() == ledger_before
    assert result["artifact_path"]
    artifacts = read_verification_artifacts(layout)
    assert artifacts == [
        {
            "id": f"artifact-{obligation['id']}",
            "obligation_id": obligation["id"],
            "artifact_path": result["artifact_path"],
            "checker_kind": "z3",
            "checked_at": "2026-06-18T00:00:00Z",
            "status": "discharged",
        }
    ]
    latest = read_proof_obligations(layout)[-1]
    assert latest["status"] == "discharged"


def test_refutation_records_countermodel(tmp_path: Path) -> None:
    """REQ-PROOF-004: disproved checker result records countermodel and refutes."""
    layout = _workspace(tmp_path)
    append_claim(layout, _claim())
    ledger_before = layout.ledger.read_bytes()
    obligation = open_pending_obligation(
        layout,
        claim_id="clm-2026-000001",
        statement="For all x, x equals x.",
        checker_kind="z3",
    )

    def checker(record: dict) -> dict:
        return {"status": "disproved", "countermodel": {"x": "witness"}}

    result = run_checker(
        layout,
        obligation["id"],
        checker_dispatch={"z3": checker},
        checked_at="2026-06-18T00:00:00Z",
    )

    assert result["status"] == "refuted"
    assert layout.ledger.read_bytes() == ledger_before
    assert result["countermodel_path"]
    countermodel = json.loads((layout.root / result["countermodel_path"]).read_text(encoding="utf-8"))
    assert countermodel == {"x": "witness"}
    latest = read_proof_obligations(layout)[-1]
    assert latest["status"] == "refuted"


def test_scientific_claim_check_flags_underreported() -> None:
    """REQ-PROOF-007: deterministic scientific check flags missing reporting."""
    underreported = check_scientific_claim(
        {
            "claim_id": "clm-2026-000001",
            "canonical_text": "The treatment improved outcomes by 12.",
            "claim_type": "result",
        }
    )
    complete = check_scientific_claim(
        {
            "claim_id": "clm-2026-000002",
            "canonical_text": (
                "The treatment improved outcomes by 12 mg +/- 2 mg "
                "(95% CI 8 to 16; n=40; p=0.03)."
            ),
            "claim_type": "result",
        }
    )

    assert {row["checker_kind"] for row in underreported} == {"units", "stats-report"}
    assert {row["class"] for row in underreported} == {
        "scientific-claim-missing-units",
        "statistical-claim-underreported",
    }
    assert complete == []


def test_checker_runs_offline_replayable(tmp_path: Path) -> None:
    """REQ-PROOF-008: rerun replays from artifact without invoking checker."""
    layout = _workspace(tmp_path)
    append_claim(layout, _claim())
    obligation = open_pending_obligation(
        layout,
        claim_id="clm-2026-000001",
        statement="For all x, x equals x.",
        checker_kind="z3",
    )
    calls = {"count": 0}

    def checker(record: dict) -> dict:
        calls["count"] += 1
        return {"status": "proved", "artifact": {"solver": "stub", "result": "valid"}}

    first = run_checker(
        layout,
        obligation["id"],
        checker_dispatch={"z3": checker},
        checked_at="2026-06-18T00:00:00Z",
    )
    second = run_checker(
        layout,
        obligation["id"],
        checker_dispatch={"z3": lambda record: (_ for _ in ()).throw(RuntimeError("network"))},
        checked_at="2026-06-19T00:00:00Z",
    )

    assert calls["count"] == 1
    assert first["status"] == second["status"] == "discharged"
    assert second["replayed"] is True
    assert first["artifact_path"] == second["artifact_path"]

    store = CozoStore.in_memory(SCHEMA)
    project_ledger(layout, store)
    assert store.query("?[id] := *proof_obligation{id}")
    assert store.query("?[id] := *verification_artifact{id}")
