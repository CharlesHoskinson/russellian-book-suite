"""CLI orchestrator. Runs the full audit and writes the bundle to docs/audits/.

Usage:
  python -m scripts.run --batch-id 2026-05-21-001
  python -m scripts.run --batch-id 2026-05-21-001 --auto-accept   # skip operator gate
  python -m scripts.run --batch-id 2026-05-21-001 --skip-expansion  # skip stage 4
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_AUDIT_ROOT = _HERE.parent
_REPO_ROOT = _AUDIT_ROOT.parent.parent
sys.path.insert(0, str(_AUDIT_ROOT))

from scripts.health_check import run_all_health_checks
from scripts.report import render_health_check_md, render_summary_md, render_readme_md, render_lint_report_md, render_expansion_md


# Base directory holding all audit bundles. The per-run bundle is nested under a
# batch-scoped subdirectory (see _bundle_root) so successive runs do not clobber each
# other's reports.
_AUDIT_BUNDLE_BASE = _REPO_ROOT / "docs" / "audits" / "russellian-style"
_AUDIT_FIXTURES = _AUDIT_ROOT / "tests" / "fixtures"


def _bundle_root(batch_id: str) -> Path:
    """Per-batch bundle root. Incorporating batch_id keeps each run's README /
    health-check / samples isolated instead of overwriting a shared fixed path
    (finding audit-bundle-path-not-batch-scoped)."""
    return _AUDIT_BUNDLE_BASE / batch_id


def _samples_exit_code(per_mode_rows, *, strict: bool) -> int:
    """Exit code contribution from the sample-lint stage. Under --strict, any FAIL
    verdict gates the run with a nonzero exit so CI/operators can act on the lint
    result rather than only the health check (finding audit-exit-ignores-sample-failures)."""
    if strict and any(row["verdict"] == "FAIL" for row in per_mode_rows):
        return 1
    return 0


def _verdict_from_results(results) -> str:
    if any(r.status == "FAIL" for r in results):
        return "FAIL"
    if any(r.status == "WARN" for r in results):
        return "WARN"
    return "PASS"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--auto-accept", action="store_true")
    parser.add_argument("--skip-expansion", action="store_true")
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit nonzero if any generated sample's lint verdict is FAIL (gates CI on the lint result).",
    )
    parser.add_argument(
        "--promote", action="store_true",
        help="Append verified entries into the committed russellian-style corpus assets. "
             "Without this flag the expansion is staged into the batch run dir only.",
    )
    args = parser.parse_args()

    bundle = _bundle_root(args.batch_id)
    bundle.mkdir(parents=True, exist_ok=True)
    samples_dir = bundle / "samples"
    samples_dir.mkdir(exist_ok=True)
    run_dir = bundle / "runs" / args.batch_id  # intermediate candidates/verified/staged outputs

    # Stage 1 — health check
    results = run_all_health_checks(fixtures_dir=_AUDIT_FIXTURES)
    (bundle / "health-check.md").write_text(render_health_check_md(results), encoding="utf-8")
    health_verdict = _verdict_from_results(results)
    if health_verdict == "FAIL":
        readme = render_readme_md(
            health_verdict="FAIL",
            expansion_verdict="SKIPPED (health check failed)",
            samples_verdict="SKIPPED (health check failed)",
            batch_id=args.batch_id,
        )
        (bundle / "README.md").write_text(readme, encoding="utf-8")
        print("Health check FAILED. See", bundle / "health-check.md")
        return 1

    # Stage 2 — expansion (optional)
    if args.skip_expansion:
        (bundle / "expansion.md").write_text("# Expansion\n\nSkipped via --skip-expansion.\n", encoding="utf-8")
        expansion_verdict = "SKIPPED"
    else:
        from scripts.expansion import run_expansion_batch
        from scripts.operator_gate import prompt_operator
        # Source path: cached Gutenberg HTML. Convention: build-russell-corpus's source cache.
        source_path = _REPO_ROOT / "tools" / "build-russell-corpus" / "tests" / "fixtures" / "source_cache" / "problems_subset.html"
        if not source_path.exists():
            print(f"Source cache missing at {source_path}. Run scrapling-fetch or supply a path; aborting expansion stage.")
            (bundle / "expansion.md").write_text(
                f"# Expansion\n\nAborted: source cache missing at {source_path}.\n",
                encoding="utf-8",
            )
            expansion_verdict = "ABORTED"
        else:
            def gate(sample_path, n_sample, n_verified):
                if args.auto_accept:
                    return ["accept"] * n_sample
                return prompt_operator(sample_path, n_sample, n_verified)
            result = run_expansion_batch(
                batch_id=args.batch_id,
                source_id="problems",
                source_path=source_path,
                n=50,
                run_dir=run_dir,
                operator_decision_fn=gate,
                promote=args.promote,
            )
            if result["appended"]:
                expansion_verdict = f"PASS (appended {result['n_verified']} entries)"
            elif result.get("staged"):
                expansion_verdict = (
                    f"STAGED ({result['n_verified']} entries in {run_dir}; "
                    "re-run with --promote to write the committed corpus)"
                )
            else:
                expansion_verdict = f"HALTED ({result['halt_reason']})"
            (bundle / "expansion.md").write_text(render_expansion_md(
                batch_id=args.batch_id,
                n_candidates=result["n_candidates"],
                n_passed_sentinel=result["n_passed_sentinel"],
                n_verified=result["n_verified"],
                n_rejected=result["n_rejected"],
                appended=result["appended"],
                halt_reason=result.get("halt_reason"),
                sample_accepted=result.get("sample_accepted", []),
            ), encoding="utf-8")

    # Stage 3 — generate + lint samples
    from scripts.generate_samples import generate_all_samples
    from scripts.lint_samples import lint_sample_file

    generation_results = generate_all_samples(out_dir=samples_dir)

    per_mode_rows = []
    samples_pass_count = 0
    for gen in generation_results:
        mode = gen["mode"]
        sample_path = samples_dir / f"{mode}.md"
        lint_result = lint_sample_file(sample_path)
        (samples_dir / f"{mode}-lint.md").write_text(render_lint_report_md(
            mode=mode,
            per_rule=lint_result["per_rule"],
            gating_count=lint_result["gating_count"],
            advisory_count=lint_result["advisory_count"],
            verdict=lint_result["verdict"],
        ), encoding="utf-8")
        per_mode_rows.append({
            "mode": mode,
            "gating": lint_result["gating_count"],
            "advisory": lint_result["advisory_count"],
            "verdict": lint_result["verdict"],
        })
        if lint_result["verdict"] == "PASS":
            samples_pass_count += 1

    (samples_dir / "summary.md").write_text(render_summary_md(per_mode_rows), encoding="utf-8")
    samples_verdict = f"{samples_pass_count}/3 modes PASS"

    # README
    (bundle / "README.md").write_text(render_readme_md(
        health_verdict=health_verdict,
        expansion_verdict=expansion_verdict,
        samples_verdict=samples_verdict,
        batch_id=args.batch_id,
    ), encoding="utf-8")

    print(f"Audit bundle written to {bundle}")
    exit_code = _samples_exit_code(per_mode_rows, strict=args.strict)
    if exit_code:
        print(f"Sample lint FAILED in {samples_pass_count}/3 modes (--strict).")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
