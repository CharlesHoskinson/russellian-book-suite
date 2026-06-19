"""Tests for kg-prose eval metrics (REQ-EVAL-002,005,006)."""
from __future__ import annotations

from pathlib import Path

from scripts.eval_harness import collect_side_products, load_gold, load_task
from scripts.eval_metrics import evaluate_metrics, score_attribution

TASK_DIR = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "eval"
    / "kg-prose"
    / "task-claim-first-mini"
)


def _metrics() -> dict:
    task = load_task(TASK_DIR)
    side_products = collect_side_products(task)
    return evaluate_metrics(task, side_products, load_gold(task))


def test_all_families_scored() -> None:
    """REQ-EVAL-002: all six metric families return honest result records."""
    metrics = _metrics()

    assert set(metrics["families"]) == {
        "attribution",
        "factuality",
        "reasoning",
        "contradiction",
        "rigor",
        "fusion",
    }
    assert metrics["families"]["attribution"]["status"] == "scored"
    assert metrics["families"]["factuality"]["status"] == "scored"
    for family in ("reasoning", "contradiction", "rigor", "fusion"):
        assert metrics["families"][family]["status"] == "unscored"
        assert metrics["families"][family]["reason"]


def test_factuality_partition_total() -> None:
    """REQ-EVAL-002: factuality partitions every atomic fact exactly once."""
    factuality = _metrics()["families"]["factuality"]

    partitions = factuality["partitions"]
    assert set(partitions) == {
        "verified-claim-backed",
        "disputed-claim-backed",
        "no-claim-binding",
        "span-check-failed",
    }
    assert sum(partitions.values()) == factuality["atomic_fact_count"]


def test_comparative_reports_both_arms() -> None:
    """REQ-EVAL-005: comparative metrics report treatment, control, and delta."""
    comparison = _metrics()["comparatives"]["claim-first-vs-flat"]

    assert comparison["status"] == "scored"
    assert comparison["treatment"]["arm"] == "claim-first-bundle"
    assert comparison["control"]["arm"] == "flat-claim-list"
    assert comparison["delta"] == (
        comparison["treatment"]["raw_score"] - comparison["control"]["raw_score"]
    )


def test_missing_gold_is_unscored() -> None:
    """REQ-EVAL-006: absent dependent gold yields unscored, not a false zero."""
    task = load_task(TASK_DIR)
    side_products = collect_side_products(task)

    result = score_attribution(side_products, {})

    assert result["status"] == "unscored"
    assert "score" not in result
    assert result["reason"]
