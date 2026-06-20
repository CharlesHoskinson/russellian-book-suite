"""Tests for the frozen kg-prose eval corpus (REQ-EVAL-001)."""
from __future__ import annotations

from pathlib import Path

from scripts.eval_harness import hash_input_files, load_task, run_task, task_input_files

TASK_DIR = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "eval"
    / "kg-prose"
    / "task-claim-first-mini"
)


def test_task_bundle_complete() -> None:
    """REQ-EVAL-001: a frozen task has snapshot, contract, and gold side product."""
    task = load_task(TASK_DIR)

    assert task.task_id == "task-claim-first-mini"
    assert task.snapshot_dir.is_dir()
    assert task.ledger_path.is_file()
    assert task.contract_path.is_file()
    assert task.gold_dir.is_dir()
    assert any(task.gold_dir.iterdir())


def test_task_immutable() -> None:
    """REQ-EVAL-001: a harness run leaves snapshot and gold bytes unchanged."""
    before = hash_input_files(task_input_files(TASK_DIR))

    run_task(TASK_DIR, run_id="pytest-immutable")

    after = hash_input_files(task_input_files(TASK_DIR))
    assert after == before
