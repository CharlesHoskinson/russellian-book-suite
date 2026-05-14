"""Aggregate per-persona review reports under a panel and compute verdict."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .load_panel import Panel
from .sibling_skills import load_book_review_module


_PLACEHOLDER_TEXTS = {"_(none)_", "(none)", "_none_", "none"}


def _is_placeholder(text: str) -> bool:
    stripped = text.strip().lower().strip("_*-").strip()
    return stripped in {"(none)", "none"} or text.strip() in _PLACEHOLDER_TEXTS


def _format_path(template: str, chapter_id: str) -> str:
    return template.replace("{chapter_id}", chapter_id)


def _count_real(findings: list) -> int:
    return sum(1 for f in findings if not _is_placeholder(f.text))


def run_aggregation(workspace: Path, chapter_id: str, panel: Panel) -> dict:
    """Read per-persona reports, compute verdict, write verdict.json + panel-review.md.

    Returns the verdict dict.
    """
    workspace = Path(workspace).resolve()
    aggregate_reviews = load_book_review_module("aggregate_reviews")
    aggregated = aggregate_reviews.aggregate_reviews(workspace, chapter_id)

    persona_gates = {p.id: p.severity_gate for p in panel.personas}

    gating_criticals = 0
    advisory_criticals = 0
    per_persona: dict[str, dict[str, int]] = {}

    dispatch_review = load_book_review_module("dispatch_review")
    reviews_dir = workspace / "chapters" / "drafts" / chapter_id / "reviews"
    for path in sorted(reviews_dir.glob("*.md")):
        try:
            r = dispatch_review.parse_review_report(path)
        except (ValueError, KeyError):
            continue
        c = _count_real(r.critical)
        i = _count_real(r.important)
        m = _count_real(r.minor)
        per_persona[r.persona_id] = {"critical": c, "important": i, "minor": m}
        gate = persona_gates.get(r.persona_id, "advisory")
        if gate == "gating":
            gating_criticals += c
        else:
            advisory_criticals += c

    # The hard_gate field is reserved for future use per the spec
    # (docs/specs/2026-05-13-review-conductor-design.md, "Invariants").
    # v1 always produces "pass" or "soft-gate-fail"; "hard-gate-fail" stays
    # in the schema enum for the future deterministic-failure hook.
    result = None

    if result is None:
        rule = panel.verdict.soft_gate_rule
        if rule == "any_critical_from_gating":
            result = "soft-gate-fail" if gating_criticals > 0 else "pass"
        elif rule == "any_critical":
            result = "soft-gate-fail" if (gating_criticals + advisory_criticals) > 0 else "pass"
        elif rule == "majority_critical":
            total = len(panel.personas)
            critical_personas = sum(
                1 for stats in per_persona.values() if stats["critical"] > 0
            )
            result = "soft-gate-fail" if critical_personas > total / 2 else "pass"
        else:
            result = "pass"

    report_path = _format_path(panel.output.panel_report_path, chapter_id)
    verdict_rel_path = _format_path(panel.output.verdict_path, chapter_id)

    verdict = {
        "panel_id": panel.panel_id,
        "artifact": {"type": "chapter", "id": chapter_id},
        "verdict": result,
        "gating_criticals": gating_criticals,
        "advisory_criticals": advisory_criticals,
        "per_persona": per_persona,
        "report_path": report_path,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    (workspace / verdict_rel_path).parent.mkdir(parents=True, exist_ok=True)
    (workspace / verdict_rel_path).write_text(
        json.dumps(verdict, indent=2), encoding="utf-8",
    )
    # The panel-review.md is produced by book-review's aggregate_reviews at
    # chapters/drafts/<chapter>/persona-review.md. Mirror it to the conductor's
    # configured path if they differ.
    source = aggregated.report_path
    target = workspace / report_path
    if source.resolve() != target.resolve():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    return verdict
