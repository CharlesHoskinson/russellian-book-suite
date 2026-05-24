"""Orchestrator for the review-revise-validate cycle.

Composes 6 stages:
  1. panel-before  (subprocess: book-review review_pass)
  2. aggregate-before  (subprocess: book-review aggregate_reviews)
  3. synthesize  (in-process: scripts.synthesize_findings)
  4. revise + apply  (in-process: scripts.revise)
  5. panel-after + aggregate-after  (subprocess again)
  6. cycle-report  (in-process: scripts.cycle_report)

Satisfies REQ-REVISE-001 (end-to-end run), REQ-REVISE-004 (optional claim
validation when workspace has a ledger), REQ-REVISE-006 (reuses aggregator),
REQ-REVISE-007 (early exit on zero Critical findings).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


_SUITE_ROOT_DEFAULT = Path(r"c:/governance/russellian-book-suite")
_CRITICAL_COUNT_RE = re.compile(r"^-\s+Critical:\s+(\d+)\s*$", re.MULTILINE)

MIN_PERSONAS_QUORUM = 4  # tolerate transient gemma4 empty-responses on up to 3 personas


def _suite_root() -> Path:
    """Locate the russellian-book-suite root (env var > default)."""
    env = os.environ.get("RUSSELLIAN_BOOK_SUITE_ROOT")
    return Path(env) if env else _SUITE_ROOT_DEFAULT


def _book_review_python() -> Path:
    return _suite_root() / "skills" / "book-review" / ".venv" / "Scripts" / "python.exe"


def _book_review_root() -> Path:
    return _suite_root() / "skills" / "book-review"


def _parse_critical_count(summary_path: Path) -> int:
    """Extract Critical count from a panel-summary.md (0 if absent)."""
    text = summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""
    m = _CRITICAL_COUNT_RE.search(text)
    return int(m.group(1)) if m else 0


def _stage1_panel(*, chapter_id: str, draft_path: Path, output_dir: Path, model: str) -> None:
    """Stage 1: run book-review panel via ollama.

    Tolerates partial success: review_pass exits 1 when any persona had a
    transient LLM failure (gemma4 occasionally returns empty responses on
    pattern-scanning personas). The cycle proceeds if at least
    MIN_PERSONAS_QUORUM persona artifacts were produced.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(_book_review_python()), "-m", "scripts.review_pass",
        "--chapter-id", chapter_id,
        "--draft-path", str(draft_path),
        "--output-dir", str(output_dir),
        "--llm-backend", "ollama",
        "--model", model,
    ]
    result = subprocess.run(cmd, cwd=str(_book_review_root()))
    persona_files = list(output_dir.glob("persona-review-*.md"))
    if len(persona_files) < MIN_PERSONAS_QUORUM:
        raise RuntimeError(
            f"stage 1 (panel) produced only {len(persona_files)} persona artifact(s) "
            f"(quorum {MIN_PERSONAS_QUORUM}); exit code {result.returncode}"
        )
    if result.returncode != 0:
        print(
            f"[run_cycle] stage 1: partial success — "
            f"{len(persona_files)}/7 personas produced output (quorum met)",
            file=sys.stderr,
        )


def _stage2_aggregate(*, panel_dir: Path, output_path: Path, chapter_id: str) -> None:
    """Stage 2: run book-review aggregate_reviews."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(_book_review_python()), "-m", "scripts.aggregate_reviews",
        "--reviews-dir", str(panel_dir),
        "--chapter-id", chapter_id,
        "--output", str(output_path),
    ]
    result = subprocess.run(cmd, cwd=str(_book_review_root()))
    if result.returncode != 0:
        raise RuntimeError(f"stage 2 (aggregate) failed with exit {result.returncode}")


def _stage3_synthesize(*, panel_summary: Path, chapter_id: str, output_path: Path) -> None:
    """Stage 3: synthesize_findings (in-process)."""
    from scripts.synthesize_findings import main as synthesize_main
    rc = synthesize_main([
        "--panel-summary", str(panel_summary),
        "--chapter-id", chapter_id,
        "--output", str(output_path),
    ])
    if rc != 0:
        raise RuntimeError(f"stage 3 (synthesize) failed with exit {rc}")


def _stage4_revise(*, chapter_path: Path, instructions_path: Path,
                   output_dir: Path, chapter_id: str, model: str) -> None:
    """Stage 4: revise (in-process)."""
    from scripts.revise import main as revise_main
    rc = revise_main([
        "--chapter", str(chapter_path),
        "--instructions", str(instructions_path),
        "--output-dir", str(output_dir),
        "--chapter-id", chapter_id,
        "--model", model,
    ])
    if rc != 0:
        raise RuntimeError(f"stage 4 (revise) failed with exit {rc}")


def run_cycle(
    *,
    chapter_id: str,
    draft_path: Path,
    workspace_dir: Path,
    model: str = "gemma4:31b",
    skip_revise: bool = False,
    skip_revalidate: bool = False,
) -> int:
    """Run the full cycle. Returns exit code."""
    workspace_dir.mkdir(parents=True, exist_ok=True)

    panel_before_dir = workspace_dir / "panel-before"
    panel_summary_before = workspace_dir / "panel-summary-before.md"
    revision_instructions = workspace_dir / "revision-instructions.md"
    revised_chapter = workspace_dir / "revised-chapter.md"
    panel_after_dir = workspace_dir / "panel-after"
    panel_summary_after = workspace_dir / "panel-summary-after.md"
    cycle_report_path = workspace_dir / "cycle-report.md"

    # Stages 1, 2
    print(f"[run_cycle] stage 1: panel-before -> {panel_before_dir}", file=sys.stderr)
    _stage1_panel(chapter_id=chapter_id, draft_path=draft_path,
                  output_dir=panel_before_dir, model=model)
    print(f"[run_cycle] stage 2: aggregate-before -> {panel_summary_before}", file=sys.stderr)
    _stage2_aggregate(panel_dir=panel_before_dir, output_path=panel_summary_before,
                      chapter_id=chapter_id)

    # REQ-REVISE-007: early exit on zero Critical findings
    critical_before = _parse_critical_count(panel_summary_before)
    if critical_before == 0 or skip_revise:
        msg = ("no Critical findings; revision skipped" if critical_before == 0
               else "--skip-revise requested")
        cycle_report_path.write_text(
            f"# Cycle report — {chapter_id}\n\n{msg}\n", encoding="utf-8")
        print(f"[run_cycle] EARLY EXIT: {msg}", file=sys.stderr)
        return 0

    # Stages 3, 4
    print(f"[run_cycle] stage 3: synthesize -> {revision_instructions}", file=sys.stderr)
    _stage3_synthesize(panel_summary=panel_summary_before, chapter_id=chapter_id,
                       output_path=revision_instructions)
    print(f"[run_cycle] stage 4: revise -> {revised_chapter}", file=sys.stderr)
    _stage4_revise(chapter_path=draft_path, instructions_path=revision_instructions,
                   output_dir=workspace_dir, chapter_id=chapter_id, model=model)

    if skip_revalidate:
        print(f"[run_cycle] EARLY EXIT: --skip-revalidate requested", file=sys.stderr)
        return 0

    # Stage 5: panel-after + aggregate-after
    print(f"[run_cycle] stage 5a: panel-after -> {panel_after_dir}", file=sys.stderr)
    _stage1_panel(chapter_id=chapter_id, draft_path=revised_chapter,
                  output_dir=panel_after_dir, model=model)
    print(f"[run_cycle] stage 5b: aggregate-after -> {panel_summary_after}", file=sys.stderr)
    _stage2_aggregate(panel_dir=panel_after_dir, output_path=panel_summary_after,
                      chapter_id=chapter_id)

    # Stage 6: cycle-report
    print(f"[run_cycle] stage 6: cycle-report -> {cycle_report_path}", file=sys.stderr)
    from scripts.cycle_report import main as cycle_report_main
    rc = cycle_report_main([
        "--before", str(panel_summary_before),
        "--after", str(panel_summary_after),
        "--chapter-id", chapter_id,
        "--output", str(cycle_report_path),
    ])
    if rc != 0:
        raise RuntimeError(f"stage 6 (cycle_report) failed with exit {rc}")

    # REQ-REVISE-004 (optional): book-knowledge claim validation
    candidate = workspace_dir.parent
    for _ in range(5):
        ledger = candidate / "claims" / "ledger.jsonl"
        if ledger.exists() and ledger.stat().st_size > 0:
            print(f"[run_cycle] REQ-REVISE-004: claim ledger found at {ledger}; running validation",
                  file=sys.stderr)
            bk_python = _suite_root() / "skills" / "book-knowledge" / ".venv" / "Scripts" / "python.exe"
            bk_root = _suite_root() / "skills" / "book-knowledge"
            cmd = [
                str(bk_python), "-m", "scripts.claim_validator",
                "--chapter", str(revised_chapter),
                "--ledger", str(ledger),
            ]
            try:
                result = subprocess.run(cmd, cwd=str(bk_root), capture_output=True, text=True)
                with cycle_report_path.open("a", encoding="utf-8") as f:
                    f.write("\n## Post-apply claim validation\n\n")
                    f.write("```\n")
                    f.write(result.stdout or "(no stdout)")
                    f.write("\n```\n")
            except Exception as e:
                print(f"[run_cycle] claim validation failed (non-fatal): {e}", file=sys.stderr)
            break
        candidate = candidate.parent
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter-id", required=True)
    parser.add_argument("--draft-path", type=Path, required=True)
    parser.add_argument("--workspace-dir", type=Path, default=None)
    parser.add_argument("--model", default="gemma4:31b")
    parser.add_argument("--skip-revise", action="store_true")
    parser.add_argument("--skip-revalidate", action="store_true")
    args = parser.parse_args(argv)

    if args.workspace_dir is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        args.workspace_dir = Path("workspace/review-cycle") / args.chapter_id / ts

    return run_cycle(
        chapter_id=args.chapter_id,
        draft_path=args.draft_path,
        workspace_dir=args.workspace_dir,
        model=args.model,
        skip_revise=args.skip_revise,
        skip_revalidate=args.skip_revalidate,
    )


if __name__ == "__main__":
    sys.exit(main())
