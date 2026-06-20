"""Stage 6 of the review-revise-validate cycle.

Reads two panel-summary.md files (before + after); computes per-persona
verdict deltas + aggregate Critical/Important/Minor count deltas; emits
cycle-report.md with regression warnings per REQ-REVISE-005.

Satisfies REQ-REVISE-003 (before/after counts at top of report) and
REQ-REVISE-005 (regression warning when after Critical > before Critical).
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


_COUNT_RE = re.compile(r"^-\s+(Critical|Important|Minor):\s+(\d+)\s*$", re.MULTILINE)
_VERDICT_RE = re.compile(r"^-\s+([a-z0-9_\-]+):\s+(APPROVED|APPROVED_WITH_NOTES|NEEDS_WORK|REJECT)\s*$", re.MULTILINE)


@dataclass
class PanelSummary:
    critical_total: int = 0
    important_total: int = 0
    minor_total: int = 0
    verdicts: dict[str, str] = field(default_factory=dict)


@dataclass
class Diff:
    critical_delta: int
    important_delta: int
    minor_delta: int
    regression: bool
    verdict_changes: dict[str, tuple[str, str]] = field(default_factory=dict)


def parse_panel_summary(path: Path) -> PanelSummary:
    """Extract aggregate counts + per-persona verdicts from a panel-summary.md."""
    text = path.read_text(encoding="utf-8")
    s = PanelSummary()
    for m in _COUNT_RE.finditer(text):
        tier = m.group(1).lower()
        count = int(m.group(2))
        setattr(s, f"{tier}_total", count)
    for m in _VERDICT_RE.finditer(text):
        s.verdicts[m.group(1)] = m.group(2)
    return s


def compute_diff(before: PanelSummary, after: PanelSummary) -> Diff:
    """Diff before vs after; detect regression (Critical count increased)."""
    crit_delta = after.critical_total - before.critical_total
    imp_delta = after.important_total - before.important_total
    min_delta = after.minor_total - before.minor_total
    regression = crit_delta > 0

    verdict_changes: dict[str, tuple[str, str]] = {}
    all_personas = set(before.verdicts.keys()) | set(after.verdicts.keys())
    for p in all_personas:
        b = before.verdicts.get(p, "(absent)")
        a = after.verdicts.get(p, "(absent)")
        if b != a:
            verdict_changes[p] = (b, a)

    return Diff(
        critical_delta=crit_delta,
        important_delta=imp_delta,
        minor_delta=min_delta,
        regression=regression,
        verdict_changes=verdict_changes,
    )


def render_report_markdown(
    *,
    chapter_id: str,
    before: PanelSummary,
    after: PanelSummary,
    diff: Diff,
) -> str:
    """Emit the cycle-report.md for stage 6 output."""
    lines: list[str] = []

    if diff.regression:
        lines.append("## ⚠ REGRESSION")
        lines.append("")
        lines.append(
            f"After-panel Critical count ({after.critical_total}) "
            f"exceeds before-panel Critical count ({before.critical_total}). "
            f"Revision introduced new critical findings."
        )
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append(f"# Cycle report — {chapter_id}")
    lines.append("")

    lines.append("## Findings counts")
    lines.append("")
    lines.append("|             | Before | After | Delta |")
    lines.append("|-------------|--------|-------|-------|")
    lines.append(f"| Critical    | {before.critical_total:<6} | {after.critical_total:<5} | ({diff.critical_delta:+d})  |")
    lines.append(f"| Important   | {before.important_total:<6} | {after.important_total:<5} | ({diff.important_delta:+d})  |")
    lines.append(f"| Minor       | {before.minor_total:<6} | {after.minor_total:<5} | ({diff.minor_delta:+d})  |")
    lines.append("")

    if diff.verdict_changes:
        lines.append("## Verdicts")
        lines.append("")
        lines.append("| Persona | Before | After |")
        lines.append("|---|---|---|")
        for persona in sorted(diff.verdict_changes.keys()):
            b, a = diff.verdict_changes[persona]
            lines.append(f"| {persona} | {b} | {a} |")
        lines.append("")

    lines.append("## Net interpretation")
    lines.append("")
    if diff.regression:
        lines.append("Cycle introduced regressions. Reject revisions or refine instructions.")
    elif diff.critical_delta < 0:
        lines.append(
            f"Cycle moved the chapter forward: Critical findings down "
            f"{abs(diff.critical_delta)}."
        )
    elif diff.critical_delta == 0 and (diff.important_delta < 0 or diff.minor_delta < 0):
        lines.append("No change in Critical count; some Important/Minor findings resolved.")
    else:
        lines.append("Cycle produced no measurable improvement.")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--chapter-id", type=str, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    before = parse_panel_summary(args.before)
    after = parse_panel_summary(args.after)
    diff = compute_diff(before, after)
    md = render_report_markdown(
        chapter_id=args.chapter_id,
        before=before,
        after=after,
        diff=diff,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(md, encoding="utf-8")
    print(f"[cycle_report] regression={diff.regression} -> {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
