"""Markdown rendering for the audit bundle.

Three top-level renderers: health-check, samples summary, and README. Plus two
helpers for per-mode lint reports and the expansion summary. Each takes plain
data and returns a markdown string. No I/O — the caller writes the strings to disk.
"""

from __future__ import annotations

from typing import Any

from scripts.health_check import HealthCheckResult


def render_health_check_md(results: list[HealthCheckResult]) -> str:
    lines = ["# Health check", "", "| Check | Status | Evidence |", "| --- | --- | --- |"]
    for r in results:
        evidence = r.evidence.replace("|", "\\|")
        lines.append(f"| {r.name} | {r.status} | {evidence} |")
    return "\n".join(lines) + "\n"


def render_summary_md(per_mode: list[dict[str, Any]]) -> str:
    lines = ["# Sample texts — summary", "", "| Mode | Gating | Advisory | Verdict |", "| --- | ---: | ---: | --- |"]
    for row in per_mode:
        lines.append(f"| {row['mode']} | {row['gating']} | {row['advisory']} | {row['verdict']} |")
    return "\n".join(lines) + "\n"


def render_readme_md(
    *,
    health_verdict: str,
    expansion_verdict: str,
    samples_verdict: str,
    batch_id: str,
) -> str:
    return (
        "# russellian-style audit\n\n"
        f"**Batch ID:** `{batch_id}`\n\n"
        "## Verdicts\n\n"
        f"- Health check: **{health_verdict}**\n"
        f"- Expansion: **{expansion_verdict}**\n"
        f"- Sample texts: **{samples_verdict}**\n\n"
        "## Artifacts\n\n"
        "- [health-check.md](health-check.md)\n"
        "- [expansion.md](expansion.md)\n"
        "- [samples/summary.md](samples/summary.md)\n"
        "  - [technical-exposition.md](samples/technical-exposition.md) + [lint](samples/technical-exposition-lint.md)\n"
        "  - [narrative-editorial.md](samples/narrative-editorial.md) + [lint](samples/narrative-editorial-lint.md)\n"
        "  - [polemic.md](samples/polemic.md) + [lint](samples/polemic-lint.md)\n"
        f"- [runs/{batch_id}/](runs/{batch_id}/) — full expansion ledgers\n"
    )


def render_lint_report_md(*, mode: str, per_rule: list[dict[str, Any]],
                          gating_count: int, advisory_count: int, verdict: str) -> str:
    lines = [
        f"# Lint report — {mode}",
        "",
        "## Per-rule counts",
        "",
        "| Rule | Count | First 3 violations |",
        "| --- | ---: | --- |",
    ]
    for row in per_rule:
        first3 = "; ".join(row["first3"]) if row["first3"] else "—"
        first3_escaped = first3.replace("|", "\\|")
        lines.append(f"| {row['rule']} | {row['count']} | {first3_escaped} |")
    lines += [
        "",
        "## Totals",
        "",
        f"- Gating violations: {gating_count}",
        f"- Advisory violations: {advisory_count}",
        "",
        f"## Verdict\n\n**{verdict}**",
        "",
    ]
    return "\n".join(lines) + "\n"


def render_expansion_md(
    *,
    batch_id: str,
    n_candidates: int,
    n_passed_sentinel: int,
    n_verified: int,
    n_rejected: int,
    appended: bool,
    halt_reason: str | None,
    sample_accepted: list[str],
) -> str:
    lines = [
        f"# Expansion batch — {batch_id}",
        "",
        "## Counts",
        "",
        f"- Candidates: {n_candidates}",
        f"- Passed sentinel: {n_passed_sentinel}",
        f"- Verified: {n_verified}",
        f"- Rejected: {n_rejected}",
        "",
    ]
    if appended:
        lines += [f"## Result\n\nAppended {n_verified} verified entries to `skills/russellian-style/assets/russell-corpus/index.json`.", ""]
    else:
        lines += [f"## Result\n\nHalted before append. Reason: {halt_reason or 'unspecified'}", ""]
    if sample_accepted:
        lines += ["## Sample of accepted entries", ""]
        for s in sample_accepted[:5]:
            lines.append(f"- `{s}`")
        lines.append("")
    return "\n".join(lines) + "\n"
