"""QA hard-gate tests for proof-obligation escapes (REQ-PROOF-009)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.windows_canary

from scripts.sentinel import aggregate


def _write_gated_sentences(workspace: Path, rows: list[dict]) -> None:
    qa = workspace / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    (qa / "gated-sentences.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_gated_sentence_escape_hard_fails(tmp_path: Path) -> None:
    """REQ-PROOF-009: escaped undischarged gated prose is a hard QA failure."""
    _write_gated_sentences(
        tmp_path,
        [
            {
                "claim_id": "clm-2026-000001",
                "obligation_id": "obl-clm-2026-000001",
                "obligation_status": "pending",
                "assertion_kind": "verified",
                "chapter": "ch-01",
                "sentence": "Verified: every finite Boolean algebra has an atom.",
            }
        ],
    )

    report = aggregate(tmp_path)

    hard = [t for t in report.hard_fail_tickets if t["class"] == "gated-sentence-escape"]
    assert len(hard) == 1
    assert hard[0]["severity"] == "critical"
    assert report.hard_fail_count == 1

    _write_gated_sentences(
        tmp_path,
        [
            {
                "claim_id": "clm-2026-000001",
                "obligation_id": "obl-clm-2026-000001",
                "obligation_status": "discharged",
                "assertion_kind": "verified",
                "chapter": "ch-01",
                "sentence": "Verified: every finite Boolean algebra has an atom.",
            },
            {
                "claim_id": "clm-2026-000002",
                "obligation_id": "obl-clm-2026-000002",
                "obligation_status": "waived",
                "assertion_kind": "conjectural",
                "chapter": "ch-01",
                "sentence": "Conjectural: every distributive lattice embeds in a powerset.",
            },
        ],
    )
    clean = aggregate(tmp_path)
    assert clean.hard_fail_count == 0
    assert clean.hard_fail_tickets == []
