"""Read-only harness for frozen KG prose evaluation tasks."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import jsonschema

from .eval_metrics import evaluate_metrics
from .io_utils import read_jsonl

REPO_ROOT = Path(__file__).resolve().parents[3]
EVAL_ROOT = REPO_ROOT / "docs" / "eval" / "kg-prose"
RUN_ROOT = EVAL_ROOT / "_runs"
SIDE_PRODUCT_SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "assets"
    / "kg-prose-side-products.schema.json"
)


class DeterminismError(AssertionError):
    """Raised when a metric differs across identical inputs."""


@dataclass(frozen=True)
class EvalTask:
    task_id: str
    chapter_id: str
    task_dir: Path
    snapshot_dir: Path
    ledger_path: Path
    contract_path: Path
    draft_path: Path
    bundle_path: Path
    writer_assertions_path: Path
    draft_atomic_facts_path: Path
    gold_dir: Path
    comparatives: dict[str, Any]


@dataclass(frozen=True)
class EvalRunResult:
    task: EvalTask
    output_dir: Path
    side_products: dict[str, Any]
    metrics: dict[str, Any]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def load_task(task_dir: Path) -> EvalTask:
    """Load task metadata and resolve all frozen input paths."""
    task_dir = task_dir.resolve()
    raw = _read_json(task_dir / "task.json")

    def inside_task(key: str) -> Path:
        return task_dir / raw[key]

    return EvalTask(
        task_id=raw["task_id"],
        chapter_id=raw["chapter_id"],
        task_dir=task_dir,
        snapshot_dir=inside_task("snapshot"),
        ledger_path=inside_task("ledger"),
        contract_path=inside_task("contract"),
        draft_path=inside_task("draft"),
        bundle_path=inside_task("chapter_bundle"),
        writer_assertions_path=inside_task("writer_assertions"),
        draft_atomic_facts_path=inside_task("draft_atomic_facts"),
        gold_dir=inside_task("gold"),
        comparatives=raw.get("comparatives", {}),
    )


def task_input_files(task_dir: Path) -> list[Path]:
    """Return immutable snapshot and gold files for a task."""
    task = load_task(task_dir)
    roots = (task.snapshot_dir, task.gold_dir)
    files: list[Path] = []
    for root in roots:
        files.extend(path for path in root.rglob("*") if path.is_file())
    return sorted(files)


def hash_input_files(paths: list[Path]) -> dict[str, str]:
    """Hash files by absolute path for immutability checks."""
    out: dict[str, str] = {}
    for path in sorted(paths):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        out[str(path.resolve())] = digest
    return out


def load_gold(task: EvalTask) -> dict[str, Any]:
    """Load curated gold side products for a task."""
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


def _flatten_code_links(raw_links: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for claim_id, links in sorted(raw_links.items()):
        for link in sorted(links, key=lambda row: json.dumps(row, sort_keys=True)):
            row = {"claim-id": claim_id}
            row.update(link)
            rows.append(row)
    return rows


def validate_side_products(side_products: dict[str, Any]) -> None:
    """Validate emitted side products against the declared interchange schema."""
    schema = _read_json(SIDE_PRODUCT_SCHEMA)
    jsonschema.validate(side_products, schema)


def collect_side_products(task: EvalTask) -> dict[str, Any]:
    """Collect S1/S2 artifacts from the frozen task snapshot."""
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


def canonical(payload: Any) -> Any:
    """Return a canonical form for result-set equality comparisons."""
    if isinstance(payload, dict):
        return {key: canonical(payload[key]) for key in sorted(payload)}
    if isinstance(payload, list):
        return sorted(
            (canonical(item) for item in payload),
            key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
        )
    return payload


def assert_deterministic(name: str, func: Callable[[], Any]) -> Any:
    """Run a metric twice and fail loudly if the canonical outputs differ."""
    first = func()
    second = func()
    if canonical(first) != canonical(second):
        raise DeterminismError(f"metric {name} is non-deterministic")
    return first


def run_task(task_dir: Path, *, run_id: str = "latest") -> EvalRunResult:
    """Run a frozen task and emit side products, prose, and metrics."""
    before = hash_input_files(task_input_files(task_dir))
    task = load_task(task_dir)
    side_products = collect_side_products(task)
    gold = load_gold(task)
    metrics = assert_deterministic(
        "all-metrics",
        lambda: evaluate_metrics(task, side_products, gold),
    )

    output_dir = RUN_ROOT / task.task_id / run_id
    _write_json(output_dir / "side-products.json", side_products)
    _write_json(output_dir / "metrics.json", metrics)
    (output_dir / "prose.md").write_text(
        side_products["prose"],
        encoding="utf-8",
        newline="\n",
    )

    after = hash_input_files(task_input_files(task_dir))
    if after != before:
        raise AssertionError("frozen task snapshot or gold changed during eval run")
    return EvalRunResult(
        task=task,
        output_dir=output_dir,
        side_products=side_products,
        metrics=metrics,
    )


def assert_metric_matches_golden(task_dir: Path) -> bool:
    """Assert current metrics equal the committed golden under canonical ordering."""
    task = load_task(task_dir)
    side_products = collect_side_products(task)
    metrics = evaluate_metrics(task, side_products, load_gold(task))
    golden = load_gold(task).get("metrics")
    if golden is None:
        raise AssertionError(f"missing metric golden for {task.task_id}")
    if canonical(metrics) != canonical(golden):
        raise AssertionError(f"metric golden mismatch for {task.task_id}")
    return True
