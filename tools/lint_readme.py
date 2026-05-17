#!/usr/bin/env python3
"""Lint a Markdown file (or stdin) under russellian-style.

The 12 linter modules emit 17 rule names. Six modules emit gating rules
(8 rule names total); six modules emit advisory rules (9 rule names total).
Gating findings produce exit code 1; advisory findings are reported but
do not block.

Usage:
    python tools/lint_readme.py path/to/file.md
    cat draft.md | python tools/lint_readme.py -
"""
from __future__ import annotations
import io
import sys
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows so linter messages with Unicode
# (e.g., the existing README's ≤ characters) print without crashing cp1252.
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "sibling_skills"))
sys.path.insert(0, str(REPO / "skills" / "russellian-style"))

from skill_api import lint_fragment  # noqa: E402

# Gating rules (6 modules → 8 rule names).
GATING_RULES = {
    "no-hedging",                    # lint_hedges
    "active-voice",                  # lint_passive_voice
    "signal-density",                # lint_signal_density
    "parallel-structure",            # lint_parallel_structure
    "listicle-abstract",             # lint_listicle_abstract
    "listicle-anaphora",             # lint_listicle_abstract (variant)
    "rhythm-uniform-length",         # lint_sentence_rhythm
    "rhythm-repeated-opening",       # lint_sentence_rhythm (variant)
}

# Advisory rules (6 modules → 9 rule names).
ADVISORY_RULES = {
    "staccato-paragraph-run",        # lint_ai_staccato
    "negation-affirmation-template", # lint_ai_staccato (variant)
    "this-is-conclusion-overuse",    # lint_ai_staccato (variant)
    "abstract-subject-run",          # lint_ai_staccato (variant)
    "ai-vocabulary",                 # lint_ai_vocabulary
    "burstiness",                    # lint_burstiness
    "concrete-instance-density",     # lint_concrete_instance_density
    "epistemic-precision",           # lint_epistemic_precision
    "paragraph-motion",              # lint_paragraph_motion
}

ALL_RULES = sorted(GATING_RULES | ADVISORY_RULES)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: lint_readme.py <path|->", file=sys.stderr)
        return 2
    target = sys.argv[1]
    text = sys.stdin.read() if target == "-" else Path(target).read_text(encoding="utf-8")

    issues = lint_fragment(text, linters=ALL_RULES)
    gate = [i for i in issues if i.linter in GATING_RULES]
    adv = [i for i in issues if i.linter in ADVISORY_RULES]

    print(f"=== {target} ===")
    print(f"gating violations: {len(gate)}")
    for i in gate:
        print(f"  [GATE]  {i.linter}:{i.line}:{i.col}  {i.message}")
    print(f"advisory findings: {len(adv)}")
    for i in adv:
        print(f"  [ADV]   {i.linter}:{i.line}:{i.col}  {i.message}")
    print(f"VERDICT: {'PASS' if not gate else 'FAIL'}")
    return 1 if gate else 0


if __name__ == "__main__":
    sys.exit(main())
