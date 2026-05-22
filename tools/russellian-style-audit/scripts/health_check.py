"""Five deterministic health checks for the russellian-style skill.

Each check returns a HealthCheckResult with status PASS | WARN | FAIL and a one-line
evidence string. The orchestrator collects all five and produces health-check.md.

This module contains the dataclass and the first two checks (pytest_suite, api_smoke).
composes_with, corpus_retrieval, and system_prompts are added by later tasks.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_RUSSELLIAN_STYLE_ROOT = _REPO_ROOT / "skills" / "russellian-style"


@dataclass
class HealthCheckResult:
    name: str        # check id
    status: str      # "PASS" | "WARN" | "FAIL"
    evidence: str    # one-line summary suitable for a markdown table cell


def check_pytest_suite(tests_dir: Path | None = None) -> HealthCheckResult:
    """Invoke pytest as a subprocess against the russellian-style tests directory."""
    # Guard against recursive invocation when this module is collected by the
    # very pytest subprocess it spawns (e.g. when tests_dir points to the audit
    # tests/ folder itself).
    if os.environ.get("RUSSELLIAN_AUDIT_HEALTH_SUBPROCESS") == "1":
        return HealthCheckResult(
            name="pytest_suite",
            status="PASS",
            evidence="skipped (subprocess re-entry guard)",
        )
    target = tests_dir if tests_dir is not None else _RUSSELLIAN_STYLE_ROOT / "tests"
    if not target.exists():
        return HealthCheckResult(
            name="pytest_suite",
            status="FAIL",
            evidence=f"tests dir does not exist: {target}",
        )
    venv_python = _RUSSELLIAN_STYLE_ROOT / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")
    interpreter = str(venv_python) if venv_python.exists() else sys.executable
    env = {**os.environ, "RUSSELLIAN_AUDIT_HEALTH_SUBPROCESS": "1"}
    completed = subprocess.run(
        [interpreter, "-m", "pytest", str(target), "-q", "--tb=no"],
        capture_output=True,
        text=True,
        cwd=str(_RUSSELLIAN_STYLE_ROOT),
        env=env,
    )
    last_line = (completed.stdout or completed.stderr or "").strip().splitlines()[-1] if (completed.stdout or completed.stderr) else ""
    status = "PASS" if completed.returncode == 0 else "FAIL"
    return HealthCheckResult(
        name="pytest_suite",
        status=status,
        evidence=f"exit {completed.returncode}; {last_line}",
    )


def check_api_smoke(
    *,
    clean_path: Path,
    hedged_path: Path,
    listicle_path: Path,
) -> HealthCheckResult:
    """Smoke-test skill_api.lint_fragment against three fixture texts.

    Routes through scripts.lint_samples.lint_fragment which wraps skill_api with the
    sys.modules namespace-eviction needed to make russellian-style's internal
    importlib.import_module("scripts.lint_X") calls resolve to russellian-style's
    scripts/* instead of the audit's empty scripts package.
    """
    try:
        from scripts.lint_samples import lint_fragment  # type: ignore
        # LintIssue still needs a direct reference for isinstance checks below;
        # load it via the same path-eviction context so we get russellian-style's class.
        from scripts.lint_samples import _skill_api  # type: ignore
        LintIssue = _skill_api.LintIssue
    except Exception as exc:
        return HealthCheckResult(
            name="api_smoke",
            status="FAIL",
            evidence=f"cannot import skill_api via lint_samples: {exc}",
        )

    clean_text = clean_path.read_text(encoding="utf-8")
    hedged_text = hedged_path.read_text(encoding="utf-8")
    listicle_text = listicle_path.read_text(encoding="utf-8")

    clean_issues = lint_fragment(clean_text)
    hedged_issues = lint_fragment(hedged_text)
    listicle_issues = lint_fragment(listicle_text)

    if not all(isinstance(i, LintIssue) for i in clean_issues + hedged_issues + listicle_issues):
        return HealthCheckResult(
            name="api_smoke",
            status="FAIL",
            evidence="lint_fragment returned non-LintIssue items",
        )

    hedged_no_hedging = any(i.linter == "no-hedging" for i in hedged_issues)
    listicle_hit = any(i.linter == "listicle-abstract" for i in listicle_issues)

    if len(clean_issues) <= 1 and hedged_no_hedging and listicle_hit:
        return HealthCheckResult(
            name="api_smoke",
            status="PASS",
            evidence=f"clean={len(clean_issues)}; hedged hit no-hedging; listicle hit listicle-abstract",
        )
    return HealthCheckResult(
        name="api_smoke",
        status="FAIL",
        evidence=(
            f"clean={len(clean_issues)} (expected <=1); "
            f"hedged hit no-hedging={hedged_no_hedging}; "
            f"listicle hit listicle-abstract={listicle_hit}"
        ),
    )


def check_corpus_retrieval(*, tags: list[str]) -> HealthCheckResult:
    """For each tag, verify the corpus index is loadable and the tag appears in at least one anchor."""
    _scripts_dir = str(_RUSSELLIAN_STYLE_ROOT / "scripts")
    try:
        sys.path.insert(0, _scripts_dir)
        try:
            from retrieve_corpus_anchor import retrieve_anchor as _retrieve  # type: ignore  # noqa: F401
        finally:
            sys.path.pop(0)
    except Exception as exc:
        return HealthCheckResult(
            name="corpus_retrieval",
            status="FAIL",
            evidence=f"cannot import retrieve_corpus_anchor: {exc}",
        )
    # Load the corpus index directly to check tag membership.
    import json
    corpus_index_path = _RUSSELLIAN_STYLE_ROOT / "assets" / "russell-corpus" / "index.json"
    try:
        index = json.loads(corpus_index_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return HealthCheckResult(
            name="corpus_retrieval",
            status="FAIL",
            evidence=f"cannot load corpus index: {exc}",
        )
    per_tag: list[str] = []
    all_ok = True
    for tag in tags:
        count = sum(1 for p in index.get("paragraphs", []) if tag in p.get("tags", []))
        per_tag.append(f"{tag}={count}")
        if count == 0:
            all_ok = False
    return HealthCheckResult(
        name="corpus_retrieval",
        status="PASS" if all_ok else "FAIL",
        evidence="; ".join(per_tag),
    )


def check_system_prompts(*, modes: list[str]) -> HealthCheckResult:
    """For each mode, call system_prompt_loader.load(mode) and confirm a non-empty string with the mandate header."""
    _scripts_dir = str(_RUSSELLIAN_STYLE_ROOT / "scripts")
    try:
        sys.path.insert(0, _scripts_dir)
        try:
            from system_prompt_loader import load  # type: ignore
        finally:
            sys.path.pop(0)
    except Exception as exc:
        return HealthCheckResult(
            name="system_prompts",
            status="FAIL",
            evidence=f"cannot import system_prompt_loader: {exc}",
        )
    per_mode: list[str] = []
    all_ok = True
    for mode in modes:
        try:
            text = load(mode)
            has_mandate = "Structural mandates" in text
            per_mode.append(f"{mode}={'PASS' if has_mandate else 'FAIL(no mandate header)'}")
            if not has_mandate:
                all_ok = False
        except Exception as exc:
            per_mode.append(f"{mode}=ERROR({exc.__class__.__name__})")
            all_ok = False
    return HealthCheckResult(
        name="system_prompts",
        status="PASS" if all_ok else "FAIL",
        evidence="; ".join(per_mode),
    )


def check_composes_with(*, consumers: list[str]) -> HealthCheckResult:
    """For each consumer skill, run `python -c "from russellian_style.skill_api import lint_fragment, API_VERSION"`
    in that consumer's venv. Report per-consumer status and aggregate.
    """
    per_consumer: list[str] = []
    all_pass = True
    any_warn = False
    any_fail = False
    for consumer in consumers:
        consumer_root = _REPO_ROOT / "skills" / consumer
        venv_python = consumer_root / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")
        if not venv_python.exists():
            per_consumer.append(f"{consumer}=WARN(venv missing)")
            any_warn = True
            all_pass = False
            continue
        completed = subprocess.run(
            [str(venv_python), "-c", "from russellian_style.skill_api import lint_fragment, API_VERSION; print(API_VERSION)"],
            capture_output=True, text=True,
        )
        if completed.returncode == 0:
            per_consumer.append(f"{consumer}=PASS({completed.stdout.strip()})")
        else:
            per_consumer.append(f"{consumer}=FAIL({completed.stderr.strip()[:80]})")
            all_pass = False
            any_fail = True
    if all_pass:
        status = "PASS"
    elif any_fail:
        status = "FAIL"
    else:
        status = "WARN"
    return HealthCheckResult(
        name="composes_with",
        status=status,
        evidence="; ".join(per_consumer),
    )


def run_all_health_checks(
    *,
    fixtures_dir: Path,
    consumers: list[str] | None = None,
    tags: list[str] | None = None,
    modes: list[str] | None = None,
) -> list[HealthCheckResult]:
    """Run all five health checks in order. Returns the result list.

    The orchestrator does not raise on FAIL — the caller (run.py) inspects the list
    and decides whether to halt before stage 4 of the audit pipeline.
    """
    consumers = consumers or ["book-compose", "book-review", "book-qa", "humanizer"]
    tags = tags or ["antithesis", "concrete_example", "concession", "domain_contrast", "paragraph_turn"]
    modes = modes or ["technical-exposition", "narrative-editorial", "polemic"]
    return [
        check_pytest_suite(),
        check_api_smoke(
            clean_path=fixtures_dir / "clean.md",
            hedged_path=fixtures_dir / "hedged.md",
            listicle_path=fixtures_dir / "listicle.md",
        ),
        check_composes_with(consumers=consumers),
        check_corpus_retrieval(tags=tags),
        check_system_prompts(modes=modes),
    ]
