"""Live producer tests for proof-obligation gated sentences (REQ-PROOF-010/012/015)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.windows_canary

from scripts.proof_gate import render_live_math_science_claim


def _claim() -> dict:
    return {
        "claim_id": "clm-2026-000010",
        "canonical_text": "Every finite Boolean algebra has an atom.",
        "status": "verified",
    }


def _obligation(status: str, **extra: str) -> dict:
    return {
        "id": "obl-clm-2026-000010",
        "linked_claim": "clm-2026-000010",
        "checker_kind": "lean",
        "status": status,
        **extra,
    }


def _gated_rows(workspace: Path) -> list[dict]:
    path = workspace / "qa" / "gated-sentences.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_rendered_sentence_emits_gated_row(tmp_path: Path) -> None:
    """REQ-PROOF-010: live rendering emits the gated-sentence producer row."""
    result = render_live_math_science_claim(
        tmp_path,
        chapter="ch-01",
        claim=_claim(),
        obligation=_obligation("discharged"),
    )

    rows = _gated_rows(tmp_path)
    assert rows == [
        {
            "assertion_kind": "verified",
            "chapter": "ch-01",
            "claim_id": "clm-2026-000010",
            "obligation_id": "obl-clm-2026-000010",
            "obligation_status": "discharged",
            "sentence": "Every finite Boolean algebra has an atom.",
        }
    ]
    assert result["gated_row"] == rows[0]
    assert "Every finite Boolean algebra has an atom." in (
        tmp_path / "chapters" / "ch-01.md"
    ).read_text(encoding="utf-8")


def test_undischarged_claim_not_verified(tmp_path: Path) -> None:
    """REQ-PROOF-012: undischarged obligations do not render verified prose."""
    result = render_live_math_science_claim(
        tmp_path,
        chapter="ch-01",
        claim=_claim(),
        obligation=_obligation("pending"),
    )

    assert result["rendered"]["asserted_verified"] is False
    assert result["rendered"]["mode"] in {"omitted", "conjectural"}
    rows = _gated_rows(tmp_path)
    assert rows[0]["assertion_kind"] in {"omitted", "conjectural"}
    assert rows[0]["assertion_kind"] != "verified"
    assert rows[0]["obligation_status"] == "pending"
    assert not (tmp_path / "chapters" / "ch-01.md").exists()


def test_waived_obligation_conjectural(tmp_path: Path) -> None:
    """REQ-PROOF-015: waived obligations render conjecturally with the waiver."""
    result = render_live_math_science_claim(
        tmp_path,
        chapter="ch-01",
        claim=_claim(),
        obligation=_obligation(
            "waived",
            waiver_reason="outside the formal subset for this edition",
        ),
    )

    rows = _gated_rows(tmp_path)
    sentence = result["rendered"]["sentence"].lower()
    assert result["rendered"]["mode"] == "conjectural"
    assert rows[0]["assertion_kind"] == "conjectural"
    assert rows[0]["obligation_status"] == "waived"
    assert rows[0]["waiver_reason"] == "outside the formal subset for this edition"
    assert "conjectural" in sentence
    assert "waived" in sentence
    assert "outside the formal subset for this edition" in sentence
