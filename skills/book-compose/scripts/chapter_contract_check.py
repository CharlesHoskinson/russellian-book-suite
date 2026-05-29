"""Verify a chapter draft satisfies its contract.

Uses russellian-style's linters via load_russellian_style_module to compute
hedge_count, passive_voice_ratio, modifier_budget_violations,
parallel_structure_violations. Adds citation_token_count for leaked claim
tokens and humanizer fingerprint metrics.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .humanizer_pass import assess_draft as _assess_humanizer
from .sibling_skills import load_russellian_style_module


_CITATION_PATTERN = re.compile(r"\[clm-\d{4}-\d{6}\]")


def _find_workspace_root_from_draft(draft_path: Path) -> Path | None:
    p = Path(draft_path).resolve()
    for candidate in [p, *p.parents]:
        if (candidate / "CLAUDE.md").is_file():
            return candidate
    return None


@dataclass(frozen=True)
class ContractCheckResult:
    passes: bool
    metrics: dict
    failed_tests: list[str] = field(default_factory=list)


def _read_persona_severity_counts(review_path: Path) -> tuple[int, int, int]:
    text = review_path.read_text(encoding="utf-8")
    crit = re.search(r"^-\s*Critical:\s*(\d+)", text, re.MULTILINE)
    imp = re.search(r"^-\s*Important:\s*(\d+)", text, re.MULTILINE)
    minr = re.search(r"^-\s*Minor:\s*(\d+)", text, re.MULTILINE)
    return (
        int(crit.group(1)) if crit else 0,
        int(imp.group(1)) if imp else 0,
        int(minr.group(1)) if minr else 0,
    )


def _read_verdict_counts(verdict_path: Path) -> tuple[int, int, int, int]:
    """Read review-conductor's verdict.json. Returns (gating_crit, advisory_crit, important, minor).

    Only counts criticals that come from gating personas; advisory criticals
    surface in the report but do not block. Important and minor are summed
    across all personas.
    """
    data = json.loads(verdict_path.read_text(encoding="utf-8"))
    gating_crit = int(data.get("gating_criticals", 0))
    advisory_crit = int(data.get("advisory_criticals", 0))
    per_persona = data.get("per_persona", {})
    important = sum(int(stats.get("important", 0)) for stats in per_persona.values())
    minor = sum(int(stats.get("minor", 0)) for stats in per_persona.values())
    return gating_crit, advisory_crit, important, minor


def _compute_persona_metrics(draft_path: Path) -> dict:
    workspace_root = _find_workspace_root_from_draft(draft_path)
    if workspace_root is None:
        # No workspace root means no review could have run; the persona gate
        # must not be trivially satisfiable by drafting outside a workspace.
        return {
            "persona_critical_count": 0,
            "persona_advisory_critical_count": 0,
            "persona_important_count": 0,
            "persona_minor_count": 0,
            "persona_reviews_complete": False,
        }

    chapter_id = draft_path.parent.name
    chapter_dir = workspace_root / "chapters" / "drafts" / chapter_id

    # Prefer review-conductor's verdict.json (per-persona gating split) over
    # the legacy persona-review.md uniform count.
    verdict_path = chapter_dir / "verdict.json"
    if verdict_path.is_file() and verdict_path.stat().st_mtime >= draft_path.stat().st_mtime:
        gating, advisory, important, minor = _read_verdict_counts(verdict_path)
        return {
            # Only gating criticals soft-gate; advisory criticals surface separately.
            "persona_critical_count": gating,
            "persona_advisory_critical_count": advisory,
            "persona_important_count": important,
            "persona_minor_count": minor,
            "persona_reviews_complete": True,
        }

    review_path = chapter_dir / "panel-review.md"
    if not review_path.exists():
        review_path = chapter_dir / "persona-review.md"
    if not review_path.exists():
        return {
            "persona_critical_count": 0,
            "persona_advisory_critical_count": 0,
            "persona_important_count": 0,
            "persona_minor_count": 0,
            "persona_reviews_complete": False,
        }
    if review_path.stat().st_mtime < draft_path.stat().st_mtime:
        return {
            "persona_critical_count": 0,
            "persona_advisory_critical_count": 0,
            "persona_important_count": 0,
            "persona_minor_count": 0,
            "persona_reviews_complete": False,
        }
    crit, imp, minr = _read_persona_severity_counts(review_path)
    return {
        "persona_critical_count": crit,
        "persona_advisory_critical_count": 0,
        "persona_important_count": imp,
        "persona_minor_count": minr,
        "persona_reviews_complete": True,
    }


def _compute_metrics(draft_path: Path) -> dict:
    # Workspace-level style overrides: if the draft sits inside a workspace
    # whose root contains style-overrides.json, expose it to russellian-style
    # via the RUSSELLIAN_OVERRIDES env var before invoking its linters.
    ws_root = _find_workspace_root_from_draft(draft_path)
    if ws_root is not None:
        overrides = ws_root / "style-overrides.json"
        if overrides.exists():
            os.environ["RUSSELLIAN_OVERRIDES"] = str(overrides)

    lint_common = load_russellian_style_module("lint_common")
    lint_hedges = load_russellian_style_module("lint_hedges")
    lint_passive = load_russellian_style_module("lint_passive_voice")
    lint_signal = load_russellian_style_module("lint_signal_density")
    lint_parallel = load_russellian_style_module("lint_parallel_structure")
    lint_listicle = load_russellian_style_module("lint_listicle_abstract")
    lint_rhythm = load_russellian_style_module("lint_sentence_rhythm")

    text = lint_common.load_markdown(draft_path)
    sentences = list(lint_common.iter_sentences(text))
    sentence_count = max(len(sentences), 1)
    hedges = lint_hedges.lint_hedges(draft_path)
    passives = lint_passive.lint_passive_voice(draft_path)
    signal = lint_signal.lint_signal_density(draft_path)
    parallel = lint_parallel.lint_parallel_structure(draft_path)
    listicle = lint_listicle.lint_listicle_abstract(draft_path)
    rhythm = lint_rhythm.lint_sentence_rhythm(draft_path)
    citation_tokens = len(_CITATION_PATTERN.findall(text))
    hr = _assess_humanizer(draft_path)
    metrics = {
        "hedge_count":                  len(hedges),
        "passive_voice_ratio":          round(len(passives) / sentence_count, 3),
        "modifier_budget_violations":   len(signal),
        "parallel_structure_violations": len(parallel),
        "listicle_abstract_count":      len(listicle),
        "rhythm_violations":            len(rhythm),
        "sentence_count":               sentence_count,
        "citation_token_count":         citation_tokens,
        "ai_vocab_count":               hr.ai_vocab_count,
        "filler_count":                 hr.filler_count,
        "inflated_symbolism_count":     hr.inflated_symbolism_count,
        "ai_fingerprint_total":         hr.total_fingerprints,
        "em_dash_count":                hr.em_dash_count,
    }
    metrics.update(_compute_persona_metrics(draft_path))
    return metrics


_TEST_PATTERN = re.compile(r"^\s*([a-z_][a-z0-9_]*)\s*(==|!=|<=|>=|<|>)\s*(.+?)\s*$")


def _evaluate_test(expr: str, metrics: dict) -> bool:
    m = _TEST_PATTERN.match(expr)
    if not m:
        return True  # not a numeric metric test; skip
    metric, op, raw = m.group(1), m.group(2), m.group(3)
    if metric not in metrics:
        return True  # not a style metric; skip (preflight handles others)
    actual = metrics[metric]
    raw_norm = raw.strip().rstrip(";")
    # Boolean comparison
    if raw_norm.lower() in ("true", "false"):
        expected = raw_norm.lower() == "true"
        return {
            "==": actual == expected,
            "!=": actual != expected,
        }.get(op, True)
    try:
        expected = float(raw_norm)
    except ValueError:
        return True
    return {
        "==": actual == expected,
        "!=": actual != expected,
        "<":  actual < expected,
        "<=": actual <= expected,
        ">":  actual > expected,
        ">=": actual >= expected,
    }[op]


def check_draft(draft_path: Path, contract: dict) -> ContractCheckResult:
    metrics = _compute_metrics(Path(draft_path))
    failed: list[str] = []
    for test in contract.get("acceptance_tests", []):
        if not _evaluate_test(test, metrics):
            failed.append(test)
    return ContractCheckResult(
        passes=not failed,
        metrics=metrics,
        failed_tests=failed,
    )
