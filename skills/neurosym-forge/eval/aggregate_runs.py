#!/usr/bin/env python3
"""REQ-EVAL-054: aggregate onboarding-bench CSVs into a weekly report.

Reads every ``*.csv`` under ``--runs-dir`` (default
``skills/neurosym-forge/eval/runs``) and writes
``docs/eval/onboarding-bench-report.md`` summarising:

- reach-extract percentage
- reach-ci percentage
- top five doc gaps (paths grepped outside the doc bundle)
- top five framework gaps (non-SUCCESS outcomes)
"""
from __future__ import annotations

import argparse
import csv
import datetime
import sys
from collections import Counter
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent.parent


def load_rows(runs_dir: Path) -> list[dict]:
    rows: list[dict] = []
    if not runs_dir.exists():
        return rows
    for csv_path in sorted(runs_dir.glob("*.csv")):
        try:
            with csv_path.open(encoding="utf-8") as fh:
                rows.extend(csv.DictReader(fh))
        except OSError:
            continue
    return rows


def summarise(rows: list[dict]) -> dict:
    total = len(rows)
    reach_extract = sum(1 for r in rows if r.get("extract_passed_at"))
    reach_ci = sum(1 for r in rows if r.get("outcome") == "SUCCESS")
    gap_counter: Counter[str] = Counter()
    for r in rows:
        gaps = (r.get("doc_gaps") or "").split(";")
        for g in gaps:
            g = g.strip()
            if g:
                gap_counter[g] += 1
    failure_counter: Counter[str] = Counter()
    for r in rows:
        outcome = r.get("outcome") or ""
        if outcome and outcome != "SUCCESS":
            failure_counter[outcome] += 1
    return {
        "total": total,
        "reach_extract_pct": (reach_extract / total) if total else 0.0,
        "reach_ci_pct": (reach_ci / total) if total else 0.0,
        "top_doc_gaps": gap_counter.most_common(5),
        "top_framework_gaps": failure_counter.most_common(5),
    }


def render_report(summary: dict, generated_at: str) -> str:
    lines: list[str] = []
    lines.append("# Onboarding-bench report")
    lines.append("")
    lines.append(f"Generated: {generated_at}")
    lines.append("")
    lines.append(f"Total runs: {summary['total']}")
    lines.append(f"Reach-extract: {summary['reach_extract_pct']:.0%}")
    lines.append(f"Reach-ci: {summary['reach_ci_pct']:.0%}")
    lines.append("")
    lines.append("## Top 5 doc gaps")
    lines.append("")
    if summary["top_doc_gaps"]:
        for path, count in summary["top_doc_gaps"]:
            lines.append(f"- `{path}` ({count})")
    else:
        lines.append("_None observed._")
    lines.append("")
    lines.append("## Top 5 framework gaps")
    lines.append("")
    if summary["top_framework_gaps"]:
        for outcome, count in summary["top_framework_gaps"]:
            lines.append(f"- `{outcome}` ({count})")
    else:
        lines.append("_None observed._")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--runs-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "runs",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "docs" / "eval" / "onboarding-bench-report.md",
    )
    args = ap.parse_args(argv)
    rows = load_rows(args.runs_dir)
    summary = summarise(rows)
    generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    report = render_report(summary, generated_at)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
