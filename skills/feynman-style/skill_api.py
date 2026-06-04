"""
Public API surface of feynman-style.
"""
from __future__ import annotations

import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

API_VERSION = (0, 1)

# Add skill root to sys.path so scripts package is importable
_SKILL_ROOT = Path(__file__).resolve().parent
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------

@dataclass
class LintIssue:
    linter: str    # rule name, e.g. "reading-grade"
    line: int      # 1-indexed line
    col: int       # 1-indexed column
    message: str   # human-readable description


# ---------------------------------------------------------------------------
# Linter registry
#
# Maps rule name -> (import_module, function_name).
# The rule name matches what each linter emits in the "rule" field.
# ---------------------------------------------------------------------------

_LINTER_REGISTRY: dict[str, tuple[str, str]] = {
    "reading-grade":          ("scripts.lint_reading_grade",    "lint_reading_grade"),
    "conversational-cold":    ("scripts.lint_conversational",   "lint_conversational"),
    "latinate-diction":       ("scripts.lint_latinate_diction", "lint_latinate_diction"),
    "analogy-absent":         ("scripts.lint_concreteness",     "lint_concreteness"),
    "abstraction-heavy":      ("scripts.lint_concreteness",     "lint_concreteness"),
    "curiosity-absent":       ("scripts.lint_curiosity_markers","lint_curiosity_markers"),
    "rhythm-uniform-length":  ("scripts.lint_sentence_rhythm",  "lint_sentence_rhythm"),
    "rhythm-repeated-opening":("scripts.lint_sentence_rhythm",  "lint_sentence_rhythm"),
    "ai-vocabulary":          ("scripts.lint_ai_vocabulary",    "lint_ai_vocabulary"),
}

# Canonical set of linters to run when no subset is requested.
_DEFAULT_LINTERS = frozenset([
    "reading-grade", "conversational-cold", "latinate-diction",
    "analogy-absent", "abstraction-heavy", "curiosity-absent",
    "rhythm-uniform-length", "ai-vocabulary",
])


def _import_linter(module_name: str, func_name: str):
    import importlib
    mod = importlib.import_module(module_name)
    return getattr(mod, func_name)


def _raw_to_issue(raw: dict) -> LintIssue:
    rule = raw.get("rule") or ""
    line = raw.get("line") or raw.get("start_line") or 1
    col = raw.get("col") or 1
    # Build a message from available fields
    sentence = raw.get("sentence") or raw.get("text") or ""
    term = raw.get("term") or raw.get("phrase") or raw.get("pattern_id") or ""
    if term:
        message = f"{rule}: {term!r} in {sentence!r}" if sentence else f"{rule}: {term!r}"
    elif sentence:
        message = f"{rule}: {sentence!r}"
    else:
        message = rule
    return LintIssue(linter=rule, line=int(line), col=int(col), message=message)


# ---------------------------------------------------------------------------
# lint_fragment
# ---------------------------------------------------------------------------

def lint_fragment(text: str, linters: Optional[list[str]] = None) -> list[LintIssue]:
    """Lint a text fragment and return style issues.

    If `linters` is None, runs the default set of linters.
    If `linters` is an empty list or contains only unknown names, returns [].
    """
    if not text or not text.strip():
        return []

    active_rules: frozenset[str]
    if linters is None:
        active_rules = _DEFAULT_LINTERS
    else:
        active_rules = frozenset(linters)

    # Filter to only known rules
    known_rules = active_rules & frozenset(_LINTER_REGISTRY)
    if not known_rules:
        return []

    # Write text to a temporary file; linters expect a Path
    issues: list[LintIssue] = []
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)

    try:
        # Deduplicate by (module, func) so linters that share a function
        # (e.g. lint_concreteness covers multiple rules) only run once.
        seen_funcs: set[tuple[str, str]] = set()
        for rule in sorted(known_rules):
            entry = _LINTER_REGISTRY.get(rule)
            if entry is None:
                continue
            if entry in seen_funcs:
                continue
            seen_funcs.add(entry)
            raw_all = []
            try:
                fn = _import_linter(*entry)
                raw_all = fn(tmp_path)
            except Exception:
                pass
            for raw in raw_all:
                if raw.get("rule") in known_rules:
                    issues.append(_raw_to_issue(raw))
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass

    return issues


# ---------------------------------------------------------------------------
# classify_linter
# ---------------------------------------------------------------------------

import json as _json
from pathlib import Path as _Path


def classify_linter(rule: str) -> str:
    """Return 'surface' or 'integrity' for a rule name, per feynman-rules.json.
    Defaults to 'surface' for unknown rule names."""
    rules = _Path(__file__).resolve().parent / "assets" / "feynman-rules.json"
    data = _json.loads(rules.read_text(encoding="utf-8"))
    return data["linter_class"].get(rule, "surface")


# ---------------------------------------------------------------------------
# preserve_argument re-export
# ---------------------------------------------------------------------------

from scripts.preserve_argument import preserve_argument, PreservationReport

__all__ = ["LintIssue", "lint_fragment", "classify_linter",
           "preserve_argument", "PreservationReport"]
