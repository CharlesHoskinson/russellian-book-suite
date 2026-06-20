"""Live proof-gate integration tests (REQ-PROOF-011/013/014)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

pytestmark = pytest.mark.windows_canary

from scripts.sentinel import aggregate


def _halmos_proof_gate() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "halmos" / "scripts" / "proof_gate.py"
    spec = importlib.util.spec_from_file_location("halmos_proof_gate_for_book_qa", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load halmos proof gate from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _claim() -> dict:
    return {
        "claim_id": "clm-2026-000011",
        "canonical_text": "Every finite Boolean algebra has an atom.",
        "status": "verified",
    }


def _obligation(status: str, **extra: str) -> dict:
    return {
        "id": "obl-clm-2026-000011",
        "linked_claim": "clm-2026-000011",
        "checker_kind": "lean",
        "status": status,
        **extra,
    }


def _write_gated_sentences(workspace: Path, rows: list[dict]) -> None:
    qa = workspace / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    (qa / "gated-sentences.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_gate_reads_live_gated_sentences(tmp_path: Path) -> None:
    """REQ-PROOF-011: book-qa consumes the live producer's gated rows."""
    proof_gate = _halmos_proof_gate()
    proof_gate.render_live_math_science_claim(
        tmp_path,
        chapter="ch-01",
        claim=_claim(),
        obligation=_obligation("discharged"),
    )

    report = aggregate(tmp_path)

    assert report.hard_fail_count == 0
    assert report.hard_fail_tickets == []
    rows = [
        json.loads(line)
        for line in (tmp_path / "qa" / "gated-sentences.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert rows[0]["assertion_kind"] == "verified"
    assert rows[0]["obligation_status"] == "discharged"


def test_escaped_gated_claim_hard_fails(tmp_path: Path) -> None:
    """REQ-PROOF-013: an undischarged verified escape blocks QA."""
    _write_gated_sentences(
        tmp_path,
        [
            {
                "claim_id": "clm-2026-000011",
                "obligation_id": "obl-clm-2026-000011",
                "obligation_status": "pending",
                "assertion_kind": "verified",
                "chapter": "ch-01",
                "sentence": "Every finite Boolean algebra has an atom.",
            }
        ],
    )

    report = aggregate(tmp_path)

    hard = [t for t in report.hard_fail_tickets if t["class"] == "gated-sentence-escape"]
    assert len(hard) == 1
    assert hard[0]["source"] == "proof-obligations"
    assert hard[0]["severity"] == "critical"
    assert report.hard_fail_count == 1


def test_ownership_and_no_live_verifier(tmp_path: Path) -> None:
    """REQ-PROOF-014: live production writes only qa/ and chapters/."""
    claims = tmp_path / "claims"
    claims.mkdir()
    obligations = claims / "proof-obligations.jsonl"
    artifacts = claims / "verification-artifacts.jsonl"
    obligations.write_text(
        json.dumps(_obligation("discharged"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifacts.write_text("", encoding="utf-8")
    before_files = {path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*")}
    before_obligations = obligations.read_bytes()
    before_artifacts = artifacts.read_bytes()

    proof_gate = _halmos_proof_gate()
    proof_gate.render_live_math_science_claim(
        tmp_path,
        chapter="ch-01",
        claim=_claim(),
        obligation=_obligation("discharged"),
    )

    after_files = {path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*")}
    assert after_files - before_files == {
        "chapters",
        "chapters/ch-01.md",
        "qa",
        "qa/gated-sentences.jsonl",
    }
    assert obligations.read_bytes() == before_obligations
    assert artifacts.read_bytes() == before_artifacts
    assert not (tmp_path / "verifier-work").exists()
