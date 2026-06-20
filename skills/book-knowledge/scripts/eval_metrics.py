"""Metrics for the frozen KG prose evaluation corpus."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .io_utils import read_jsonl

FAMILIES = (
    "attribution",
    "factuality",
    "reasoning",
    "contradiction",
    "rigor",
    "fusion",
)

FACTUALITY_PARTITIONS = (
    "verified-claim-backed",
    "disputed-claim-backed",
    "no-claim-binding",
    "span-check-failed",
)


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def _unscored(reason: str) -> dict[str, Any]:
    return {
        "status": "unscored",
        "reason": reason,
        "micro": {"status": "unscored"},
        "macro": {"status": "unscored"},
    }


def _gold_sentence_spans(gold: dict[str, Any]) -> dict[str, set[str]]:
    rows = gold.get("attribution_spans", {}).get("sentences")
    if not rows:
        return {}
    return {
        str(row["assertion_id"]): set(row.get("required_span_ids", []))
        for row in rows
    }


def score_attribution(
    side_products: dict[str, Any],
    gold: dict[str, Any],
) -> dict[str, Any]:
    """Score cited sentence spans against curated gold span bindings."""
    gold_spans = _gold_sentence_spans(gold)
    if not gold_spans:
        return _unscored("missing attribution gold spans")

    cited = {
        str(row["id"]): set(row.get("cites_span", []))
        for row in side_products["writer-assertions"]
    }
    correct = 0
    cited_total = 0
    gold_total = 0
    for assertion_id, required in sorted(gold_spans.items()):
        actual = cited.get(assertion_id, set())
        correct += len(actual & required)
        cited_total += len(actual)
        gold_total += len(required)

    precision = _ratio(correct, cited_total)
    recall = _ratio(correct, gold_total)
    micro = {
        "precision": precision,
        "recall": recall,
        "sentence_count": len(gold_spans),
    }
    return {
        "status": "scored",
        "counts": {
            "correct_citations": correct,
            "cited_spans": cited_total,
            "gold_spans": gold_total,
        },
        "micro": micro,
        "macro": {
            "chapter_count": 1,
            "precision": precision,
            "recall": recall,
        },
    }


def _claim_id(record: dict[str, Any]) -> str | None:
    value = record.get("claim_id", record.get("id"))
    if value is None:
        return None
    return str(value)


def _claim_statuses(records: Iterable[dict[str, Any]]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for record in records:
        claim_id = _claim_id(record)
        if claim_id:
            statuses[claim_id] = str(record.get("status", "unknown"))
    return statuses


def _assertion_status_by_claim(
    assertions: Iterable[dict[str, Any]],
) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for assertion in assertions:
        status = assertion.get("citation_check_status")
        if status not in {"full", "partial", "none"}:
            continue
        for claim_id in assertion.get("asserts_claim", []):
            current = statuses.get(claim_id)
            if current is None or (current == "full" and status != "full"):
                statuses[str(claim_id)] = str(status)
    return statuses


def score_factuality(
    side_products: dict[str, Any],
    claim_statuses: dict[str, str],
) -> dict[str, Any]:
    """Partition S2 draft atomic facts into factuality buckets."""
    partitions = {name: 0 for name in FACTUALITY_PARTITIONS}
    assertion_status = _assertion_status_by_claim(side_products["writer-assertions"])
    for fact in side_products["draft-atomic-facts"]:
        claim_id = fact.get("claim_id")
        if not claim_id:
            partitions["no-claim-binding"] += 1
            continue
        if assertion_status.get(str(claim_id)) in {"partial", "none"}:
            partitions["span-check-failed"] += 1
            continue
        if claim_statuses.get(str(claim_id)) == "disputed":
            partitions["disputed-claim-backed"] += 1
            continue
        partitions["verified-claim-backed"] += 1

    fact_count = len(side_products["draft-atomic-facts"])
    claim_backed = (
        partitions["verified-claim-backed"]
        + partitions["disputed-claim-backed"]
        + partitions["span-check-failed"]
    )
    span_passed = (
        partitions["verified-claim-backed"]
        + partitions["disputed-claim-backed"]
    )
    micro = {
        "fact_count": fact_count,
        "claim_backed_rate": _ratio(claim_backed, fact_count),
        "span_pass_rate": _ratio(span_passed, fact_count),
    }
    return {
        "status": "scored",
        "atomic_fact_count": fact_count,
        "partitions": partitions,
        "micro": micro,
        "macro": {
            "chapter_count": 1,
            "claim_backed_rate": micro["claim_backed_rate"],
            "span_pass_rate": micro["span_pass_rate"],
        },
    }


def score_claim_first_comparative(
    side_products: dict[str, Any],
    comparison: dict[str, Any],
) -> dict[str, Any]:
    """Compare S1 claim-first bundle coverage with a flat claim-list control."""
    control_claims = comparison.get("control_flat_claims")
    if control_claims is None:
        return _unscored("missing flat claim-list control")

    treatment_score = len(side_products["selected-claims"])
    control_score = len(control_claims)
    return {
        "status": "scored",
        "treatment": {
            "arm": "claim-first-bundle",
            "raw_score": treatment_score,
        },
        "control": {
            "arm": "flat-claim-list",
            "raw_score": control_score,
        },
        "delta": treatment_score - control_score,
    }


def evaluate_metrics(
    task: Any,
    side_products: dict[str, Any],
    gold: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate every declared metric family for a frozen task."""
    claim_statuses = _claim_statuses(read_jsonl(task.ledger_path))
    families = {
        "attribution": score_attribution(side_products, gold),
        "factuality": score_factuality(side_products, claim_statuses),
        "reasoning": _unscored("reasoning proof-trace artifacts are not present"),
        "contradiction": _unscored("contradiction-alert gold is not present"),
        "rigor": _unscored("proof-obligation artifacts are not present"),
        "fusion": _unscored("cross-domain fusion artifacts are not present"),
    }
    comparison_cfg = task.comparatives.get("claim-first-vs-flat", {})
    return {
        "schema": "kg-prose-metrics/v1",
        "task-id": task.task_id,
        "families": {family: families[family] for family in FAMILIES},
        "comparatives": {
            "claim-first-vs-flat": score_claim_first_comparative(
                side_products,
                comparison_cfg,
            )
        },
    }
