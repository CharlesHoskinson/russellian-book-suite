"""Run skill_api.lint_fragment over each generated sample and produce per-mode lint reports.

The audit calls lint_fragment with the FULL 17-rule registry — not just the default 10
— so the advisory rules also fire. Reports separate gating from advisory counts.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_RUSSELLIAN_STYLE_ROOT = _REPO_ROOT / "skills" / "russellian-style"


def _load_module_by_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Load russellian-style skill_api
_skill_api = _load_module_by_path(
    "russellian_style_skill_api",
    _RUSSELLIAN_STYLE_ROOT / "skill_api.py",
)
lint_fragment = _skill_api.lint_fragment


# Mirror skill_api._LINTER_REGISTRY keys
ALL_17_RULES = [
    "no-hedging", "active-voice", "signal-density", "parallel-structure",
    "listicle-abstract", "listicle-anaphora",
    "rhythm-uniform-length", "rhythm-repeated-opening",
    "burstiness", "ai-vocabulary",
    "staccato-paragraph-run", "negation-affirmation-template",
    "this-is-conclusion-overuse", "abstract-subject-run",
    "concrete-instance-density", "epistemic-precision", "paragraph-motion",
]

# Default 10 are "gating"; the other 7 are advisory.
GATING_RULES = {
    "no-hedging", "active-voice", "signal-density", "parallel-structure",
    "listicle-abstract", "listicle-anaphora",
    "rhythm-uniform-length", "rhythm-repeated-opening",
    "burstiness", "ai-vocabulary",
}


def lint_sample(text: str) -> dict:
    """Run lint_fragment with all 17 rules and aggregate counts.

    Returns:
      {
        "per_rule": [
          {"rule": "no-hedging", "count": 0, "first3": []},
          ...
        ],
        "gating_count": int,
        "advisory_count": int,
        "verdict": "PASS" | "WARN" | "FAIL",
      }
    """
    issues = lint_fragment(text, linters=ALL_17_RULES)
    by_rule: dict[str, list] = {r: [] for r in ALL_17_RULES}
    for issue in issues:
        if issue.linter in by_rule:
            by_rule[issue.linter].append(issue)

    per_rule = []
    gating_count = 0
    advisory_count = 0
    for rule in ALL_17_RULES:
        rule_issues = by_rule[rule]
        first3 = [f"L{i.line}:C{i.col} {i.message[:60]}" for i in rule_issues[:3]]
        per_rule.append({"rule": rule, "count": len(rule_issues), "first3": first3})
        if rule in GATING_RULES:
            gating_count += len(rule_issues)
        else:
            advisory_count += len(rule_issues)

    if gating_count <= 2:
        verdict = "PASS"
    elif gating_count <= 5:
        verdict = "WARN"
    else:
        verdict = "FAIL"

    return {
        "per_rule": per_rule,
        "gating_count": gating_count,
        "advisory_count": advisory_count,
        "verdict": verdict,
    }


def lint_sample_file(sample_path: Path) -> dict:
    """Read a sample file and lint it. Result includes mode (derived from filename)."""
    mode = sample_path.stem
    result = lint_sample(sample_path.read_text(encoding="utf-8"))
    result["mode"] = mode
    return result
