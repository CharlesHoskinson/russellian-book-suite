"""Live build adapter for KG prose evaluation."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .eval_harness import assert_deterministic, hash_input_files, validate_side_products
from .eval_metrics import FAMILIES, evaluate_metrics
from .io_utils import read_jsonl


@dataclass(frozen=True)
class LiveChapterTask:
    """Minimal task object accepted by the S0 metric evaluator."""

    task_id: str
    chapter_id: str
    ledger_path: Path
    draft_path: Path
    bundle_path: Path
    writer_assertions_path: Path
    draft_atomic_facts_path: Path
    gold_dir: Path
    comparatives: dict[str, Any]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def _avg(values: list[Any]) -> float | None:
    numeric = [
        value
        for value in values
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    if not numeric:
        return None
    return round(sum(numeric) / len(numeric), 6)


def _flatten_code_links(raw_links: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for claim_id, links in sorted(raw_links.items()):
        for link in sorted(links, key=lambda row: json.dumps(row, sort_keys=True)):
            row = {"claim-id": claim_id}
            row.update(link)
            rows.append(row)
    return rows


def _as_build_path(build_root: Path, raw: str | Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return build_root / path


def _gold_root(build_root: Path, config: dict[str, Any]) -> Path:
    raw = config.get("gold_root")
    if raw is None:
        return build_root / "eval-gold"
    return _as_build_path(build_root, raw)


def _chapter_comparatives(config: dict[str, Any], chapter_id: str) -> dict[str, Any]:
    raw = config.get("comparatives", {})
    if not isinstance(raw, dict):
        return {}
    if "claim-first-vs-flat" in raw:
        return raw
    chapter_cfg = raw.get(chapter_id, {})
    if isinstance(chapter_cfg, dict):
        return chapter_cfg
    return {}


def discover_live_chapters(build_root: Path) -> list[Path]:
    """Return chapter draft directories from a live book build."""
    drafts_root = build_root / "chapters" / "drafts"
    if not drafts_root.exists():
        return []
    return sorted(
        path
        for path in drafts_root.iterdir()
        if path.is_dir() and (path / "chapter-retrieval-bundle.json").is_file()
    )


def load_live_chapter(
    build_root: Path,
    chapter_dir: Path,
    *,
    config: dict[str, Any] | None = None,
) -> LiveChapterTask:
    """Load the S0-compatible task view for one live chapter."""
    cfg = config or {}
    bundle_path = chapter_dir / "chapter-retrieval-bundle.json"
    bundle = _read_json(bundle_path)
    chapter_id = str(bundle.get("chapter-id", chapter_dir.name))
    return LiveChapterTask(
        task_id=f"live-build:{build_root.name}:{chapter_id}",
        chapter_id=chapter_id,
        ledger_path=build_root / "claims" / "ledger.jsonl",
        draft_path=chapter_dir / "draft.md",
        bundle_path=bundle_path,
        writer_assertions_path=chapter_dir / "writer-assertions.jsonl",
        draft_atomic_facts_path=chapter_dir / "draft-atomic-facts.jsonl",
        gold_dir=_gold_root(build_root, cfg) / chapter_id,
        comparatives=_chapter_comparatives(cfg, chapter_id),
    )


def load_live_gold(task: LiveChapterTask) -> dict[str, Any]:
    """Load optional live gold files for the chapter."""
    gold: dict[str, Any] = {}
    attribution_path = task.gold_dir / "attribution-spans.json"
    factuality_path = task.gold_dir / "factuality-partitions.json"
    metrics_path = task.gold_dir / "metrics.json"
    if attribution_path.exists():
        gold["attribution_spans"] = _read_json(attribution_path)
    if factuality_path.exists():
        gold["factuality_partitions"] = _read_json(factuality_path)
    if metrics_path.exists():
        gold["metrics"] = _read_json(metrics_path)
    return gold


def collect_live_side_products(task: LiveChapterTask) -> dict[str, Any]:
    """Collect live side products into the frozen S0 interchange schema."""
    bundle = _read_json(task.bundle_path)
    side_products = {
        "schema": "kg-prose-side-products/v1",
        "task-id": task.task_id,
        "chapter-id": task.chapter_id,
        "prose": task.draft_path.read_text(encoding="utf-8"),
        "selected-claims": bundle.get("load-bearing-claims", []),
        "cited-spans": bundle.get("source-span-anchors", []),
        "contradiction-alerts": bundle.get("contradiction-alerts", []),
        "warnings": bundle.get("warnings", []),
        "proof-traces": bundle.get("proof-traces", []),
        "code-links": _flatten_code_links(bundle.get("code-links", {})),
        "writer-assertions": read_jsonl(task.writer_assertions_path),
        "draft-atomic-facts": read_jsonl(task.draft_atomic_facts_path),
    }
    validate_side_products(side_products)
    return side_products


def _declared_metrics(task: LiveChapterTask, metrics: dict[str, Any]) -> dict[str, Any]:
    comparatives = metrics.get("comparatives", {})
    declared = {
        name: value
        for name, value in comparatives.items()
        if name in task.comparatives
    }
    result = dict(metrics)
    result["comparatives"] = declared
    return result


def _aggregate_unscored(family: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "unscored",
        "family": family,
        "chapter_count": len(records),
        "scored_chapter_count": 0,
        "unscored_chapter_count": len(records),
        "reason": "no scored chapter records",
    }


def _aggregate_attribution(records: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [record for record in records if record.get("status") == "scored"]
    if not scored:
        return _aggregate_unscored("attribution", records)
    correct = sum(record["counts"]["correct_citations"] for record in scored)
    cited = sum(record["counts"]["cited_spans"] for record in scored)
    gold = sum(record["counts"]["gold_spans"] for record in scored)
    precision = _ratio(correct, cited)
    recall = _ratio(correct, gold)
    return {
        "status": "scored",
        "chapter_count": len(records),
        "scored_chapter_count": len(scored),
        "unscored_chapter_count": len(records) - len(scored),
        "counts": {
            "correct_citations": correct,
            "cited_spans": cited,
            "gold_spans": gold,
        },
        "micro": {
            "precision": precision,
            "recall": recall,
            "sentence_count": sum(
                record.get("micro", {}).get("sentence_count", 0)
                for record in scored
            ),
        },
        "macro": {
            "chapter_count": len(scored),
            "precision": _avg(
                [record.get("macro", {}).get("precision") for record in scored]
            ),
            "recall": _avg([record.get("macro", {}).get("recall") for record in scored]),
        },
    }


def _aggregate_factuality(records: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [record for record in records if record.get("status") == "scored"]
    if not scored:
        return _aggregate_unscored("factuality", records)
    partitions: dict[str, int] = {}
    for record in scored:
        for name, count in record.get("partitions", {}).items():
            partitions[name] = partitions.get(name, 0) + int(count)
    fact_count = sum(int(record.get("atomic_fact_count", 0)) for record in scored)
    claim_backed = (
        partitions.get("verified-claim-backed", 0)
        + partitions.get("disputed-claim-backed", 0)
        + partitions.get("span-check-failed", 0)
    )
    span_passed = (
        partitions.get("verified-claim-backed", 0)
        + partitions.get("disputed-claim-backed", 0)
    )
    return {
        "status": "scored",
        "chapter_count": len(records),
        "scored_chapter_count": len(scored),
        "unscored_chapter_count": len(records) - len(scored),
        "atomic_fact_count": fact_count,
        "partitions": dict(sorted(partitions.items())),
        "micro": {
            "fact_count": fact_count,
            "claim_backed_rate": _ratio(claim_backed, fact_count),
            "span_pass_rate": _ratio(span_passed, fact_count),
        },
        "macro": {
            "chapter_count": len(scored),
            "claim_backed_rate": _avg(
                [record.get("macro", {}).get("claim_backed_rate") for record in scored]
            ),
            "span_pass_rate": _avg(
                [record.get("macro", {}).get("span_pass_rate") for record in scored]
            ),
        },
    }


def _aggregate_generic(family: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [record for record in records if record.get("status") == "scored"]
    if not scored:
        return _aggregate_unscored(family, records)
    return {
        "status": "scored",
        "family": family,
        "chapter_count": len(records),
        "scored_chapter_count": len(scored),
        "unscored_chapter_count": len(records) - len(scored),
    }


def aggregate_families(chapter_metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Aggregate the six metric families across live chapters."""
    aggregates: dict[str, Any] = {}
    for family in FAMILIES:
        records = [
            payload["families"][family]
            for _, payload in sorted(chapter_metrics.items())
        ]
        if family == "attribution":
            aggregates[family] = _aggregate_attribution(records)
        elif family == "factuality":
            aggregates[family] = _aggregate_factuality(records)
        else:
            aggregates[family] = _aggregate_generic(family, records)
    return aggregates


def aggregate_comparatives(chapter_metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Aggregate declared comparative metrics across live chapters."""
    names = sorted(
        {
            name
            for payload in chapter_metrics.values()
            for name in payload.get("comparatives", {})
        }
    )
    aggregates: dict[str, Any] = {}
    for name in names:
        records = [
            payload["comparatives"][name]
            for _, payload in sorted(chapter_metrics.items())
            if name in payload.get("comparatives", {})
        ]
        scored = [record for record in records if record.get("status") == "scored"]
        if not scored:
            aggregates[name] = {
                "status": "unscored",
                "chapter_count": len(records),
                "scored_chapter_count": 0,
                "unscored_chapter_count": len(records),
                "reason": "no scored comparative records",
            }
            continue
        treatment_score = sum(
            int(record["treatment"]["raw_score"]) for record in scored
        )
        control_score = sum(int(record["control"]["raw_score"]) for record in scored)
        aggregates[name] = {
            "status": "scored",
            "chapter_count": len(records),
            "scored_chapter_count": len(scored),
            "unscored_chapter_count": len(records) - len(scored),
            "treatment": {
                "arm": scored[0]["treatment"]["arm"],
                "raw_score": treatment_score,
            },
            "control": {
                "arm": scored[0]["control"]["arm"],
                "raw_score": control_score,
            },
            "delta": treatment_score - control_score,
        }
    return aggregates


def _gate_rules(config: dict[str, Any]) -> list[dict[str, Any]]:
    raw = config.get("gating", {})
    if isinstance(raw, list):
        return [rule for rule in raw if isinstance(rule, dict)]
    if not isinstance(raw, dict):
        return []
    metrics = raw.get("metrics", raw.get("rules", {}))
    if isinstance(metrics, list):
        return [rule for rule in metrics if isinstance(rule, dict)]
    if not isinstance(metrics, dict):
        return []
    rules: list[dict[str, Any]] = []
    for metric, rule in sorted(metrics.items()):
        if isinstance(rule, dict):
            item = {"metric": metric}
            item.update(rule)
            rules.append(item)
    return rules


def _metric_value(report: dict[str, Any], metric: str) -> Any:
    parts = metric.split(".")
    if len(parts) < 2:
        return None
    family = report["aggregate"]["families"].get(parts[0])
    if family is not None:
        name = ".".join(parts[1:])
        for section in ("macro", "micro"):
            if name in family.get(section, {}):
                return family[section][name]
        return family.get(name)
    comparative = report["aggregate"]["comparatives"].get(parts[0])
    if comparative is None:
        return None
    current: Any = comparative
    for part in parts[1:]:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _passes(value: float, operator: str, threshold: float) -> bool:
    if operator == ">":
        return value > threshold
    if operator == ">=":
        return value >= threshold
    if operator == "<":
        return value < threshold
    if operator == "<=":
        return value <= threshold
    if operator == "==":
        return value == threshold
    raise ValueError(f"unsupported gate operator: {operator}")


def evaluate_gating(report: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Evaluate advisory/gating status for the live build report."""
    rules = _gate_rules(config)
    if not rules:
        return {
            "mode": "advisory",
            "status": "pass",
            "failures": [],
            "rules": [],
        }

    failures: list[dict[str, Any]] = []
    observed: list[dict[str, Any]] = []
    for rule in rules:
        metric = str(rule["metric"])
        value = _metric_value(report, metric)
        threshold = rule.get("threshold")
        operator = str(rule.get("operator", ">="))
        baselined = bool(rule.get("baselined", False))
        row = {
            "metric": metric,
            "value": value,
            "operator": operator,
            "threshold": threshold,
            "baselined": baselined,
            "severity": "gating" if baselined else "advisory",
        }
        if value is None or threshold is None:
            row["status"] = "unscored"
        elif baselined:
            passed = _passes(float(value), operator, float(threshold))
            row["status"] = "pass" if passed else "fail"
            if not passed:
                failures.append(dict(row))
        else:
            row["status"] = "advisory"
        observed.append(row)

    return {
        "mode": "gating" if any(rule.get("baselined", False) for rule in rules) else "advisory",
        "status": "fail" if failures else "pass",
        "failures": failures,
        "rules": observed,
    }


def _live_input_files(build_root: Path, config: dict[str, Any]) -> list[Path]:
    roots = [
        build_root / "claims",
        build_root / "chapters" / "drafts",
        _gold_root(build_root, config),
    ]
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(path for path in root.rglob("*") if path.is_file())
    return sorted(files)


def _build_report(build_root: Path, config: dict[str, Any]) -> dict[str, Any]:
    chapter_dirs = discover_live_chapters(build_root)
    if not chapter_dirs:
        raise FileNotFoundError(f"no live chapter drafts found under {build_root}")

    chapters: dict[str, dict[str, Any]] = {}
    chapter_metrics: dict[str, dict[str, Any]] = {}
    for chapter_dir in chapter_dirs:
        task = load_live_chapter(build_root, chapter_dir, config=config)
        side_products = collect_live_side_products(task)
        metrics = _declared_metrics(
            task,
            evaluate_metrics(task, side_products, load_live_gold(task)),
        )
        chapters[task.chapter_id] = {
            "chapter-id": task.chapter_id,
            "metrics": metrics,
            "side-products": {
                "prose_character_count": len(side_products["prose"]),
                "selected_claim_count": len(side_products["selected-claims"]),
                "writer_assertion_count": len(side_products["writer-assertions"]),
                "atomic_fact_count": len(side_products["draft-atomic-facts"]),
            },
        }
        chapter_metrics[task.chapter_id] = metrics

    report = {
        "schema": "kg-prose-live-build-report/v1",
        "build-root": str(build_root),
        "chapters": chapters,
        "aggregate": {
            "families": aggregate_families(chapter_metrics),
            "comparatives": aggregate_comparatives(chapter_metrics),
        },
    }
    report["gating"] = evaluate_gating(report, config)
    return report


def score_live_build(
    build_root: Path,
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score a live build read-only and return a deterministic build report."""
    root = Path(build_root).resolve()
    cfg = config or {}
    before = hash_input_files(_live_input_files(root, cfg))
    report = assert_deterministic("live-build-report", lambda: _build_report(root, cfg))
    after = hash_input_files(_live_input_files(root, cfg))
    if before != after:
        raise AssertionError("live build side products changed during eval run")
    return report


def write_live_build_report(
    build_root: Path,
    output_path: Path | None = None,
    *,
    config: dict[str, Any] | None = None,
) -> Path:
    """Score a live build and emit its report as JSON."""
    root = Path(build_root).resolve()
    target = output_path or root / "reports" / "kg-prose-live-build-report.json"
    _write_json(target, score_live_build(root, config=config))
    return target
