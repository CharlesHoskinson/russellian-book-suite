"""Render a feynman-style pass report. Mirrors russellian-style's report shape."""
from __future__ import annotations

from collections import Counter


def render_report(findings: list[dict], delta_score: float, preservation_ok: bool) -> str:
    by_rule = Counter(f.get("rule", "?") for f in findings)
    lines = ["# Feynman style pass report", ""]
    lines.append(f"**Argument preservation (hard gate):** {'PASS' if preservation_ok else 'FAIL'}")
    lines.append(f"**Feynman delta score:** {delta_score:.2f}  (lower is closer)")
    lines.append("")
    lines.append("## Findings by rule")
    if not by_rule:
        lines.append("None.")
    for rule, n in sorted(by_rule.items()):
        lines.append(f"- `{rule}`: {n}")
    return "\n".join(lines) + "\n"
