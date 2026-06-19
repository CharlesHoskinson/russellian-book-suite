"""Tests for kg-prose eval metric goldens (REQ-EVAL-004)."""
from __future__ import annotations

from pathlib import Path

from scripts.eval_harness import assert_metric_matches_golden

TASK_DIR = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "eval"
    / "kg-prose"
    / "task-claim-first-mini"
)


def test_metric_matches_golden() -> None:
    """REQ-EVAL-004: frozen task metrics match committed canonical goldens."""
    assert_metric_matches_golden(TASK_DIR)
