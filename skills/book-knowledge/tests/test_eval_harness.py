"""Tests for kg-prose eval harness behavior (REQ-EVAL-003,007)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.eval_harness import (
    DeterminismError,
    assert_deterministic,
    load_task,
    run_task,
)

TASK_DIR = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "eval"
    / "kg-prose"
    / "task-claim-first-mini"
)


def test_run_emits_side_products() -> None:
    """REQ-EVAL-003: a run emits graph-structured side products to schema."""
    result = run_task(TASK_DIR, run_id="pytest-side-products")

    side_products_path = result.output_dir / "side-products.json"
    assert side_products_path.is_file()
    emitted = json.loads(side_products_path.read_text(encoding="utf-8"))
    assert emitted["task-id"] == load_task(TASK_DIR).task_id
    for key in (
        "selected-claims",
        "cited-spans",
        "contradiction-alerts",
        "warnings",
        "proof-traces",
        "code-links",
        "writer-assertions",
        "draft-atomic-facts",
        "prose",
    ):
        assert key in emitted


def test_determinism_guard() -> None:
    """REQ-EVAL-007: nondeterministic metrics fail loudly by metric name."""
    calls = {"count": 0}

    def unstable_metric() -> dict:
        calls["count"] += 1
        return {"value": calls["count"]}

    with pytest.raises(DeterminismError, match="unstable-metric"):
        assert_deterministic("unstable-metric", unstable_metric)
