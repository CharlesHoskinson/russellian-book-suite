"""Phase L tests: REQ-CI-040..044 — CI workflow + flake + runbook shape.

These are static-text assertions against the workflow YAML, the flake,
and the operations runbook. They run on any OS and catch matrix-shape
regressions before the runners would (e.g., a copy-paste that drops one
of the three OS labels).

REQ map:
  REQ-CI-040 — python-skill-matrix mentions all three OS labels
  REQ-CI-041 — cargo-test job exists, Linux + macOS, brew install z3
  REQ-CI-042 — ci-divergence-summary aggregator emits to GITHUB_STEP_SUMMARY
  REQ-CI-043 — flake.nix declares darwin systems via a named constant
  REQ-CI-044 — docs/operations/ci-platforms.md exists + mentions libz3 + WSL
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
CI_BUDGET = REPO_ROOT / ".github" / "workflows" / "ci-budget.yml"
MATRIX_JSON = REPO_ROOT / ".github" / "ci" / "skills-matrix.json"
SETUP_MODELS = REPO_ROOT / ".github" / "actions" / "setup-models" / "action.yml"
DEPENDABOT = REPO_ROOT / ".github" / "dependabot.yml"
FLAKE = REPO_ROOT / "flake.nix"
CI_PLATFORMS_DOC = REPO_ROOT / "docs" / "operations" / "ci-platforms.md"


def _budget_text() -> str:
    assert CI_BUDGET.exists(), f"ci-budget workflow not found at {CI_BUDGET}"
    return CI_BUDGET.read_text(encoding="utf-8")


def _matrix_config() -> dict:
    assert MATRIX_JSON.exists(), f"skills matrix registry not found at {MATRIX_JSON}"
    return json.loads(MATRIX_JSON.read_text(encoding="utf-8"))


def _dependabot_text() -> str:
    assert DEPENDABOT.exists(), f"dependabot config not found at {DEPENDABOT}"
    return DEPENDABOT.read_text(encoding="utf-8")


def _workflow_text() -> str:
    assert WORKFLOW.exists(), f"workflow not found at {WORKFLOW}"
    return WORKFLOW.read_text(encoding="utf-8")


# ---------- REQ-CI-040 ----------


def test_python_skill_matrix_has_three_oses():
    """REQ-CI-040: the default OS axis enumerates all three OSes."""
    assert _matrix_config()["defaults"]["os"] == [
        "ubuntu-24.04", "macos-15", "windows-2022",
    ]


def test_python_skill_runs_on_matrix_os():
    """REQ-CI-040: the python-skill job consumes matrix.os via runs-on."""
    text = _workflow_text()
    # The python-skill-matrix block should set runs-on to ${{ matrix.os }}
    # The cargo-test job does too; either occurrence proves the pattern.
    assert "runs-on: ${{ matrix.os }}" in text, (
        "no `runs-on: ${{ matrix.os }}` line found; matrix likely not wired"
    )


def test_python_skill_matrix_fail_fast_false():
    """REQ-CI-040: matrix must use fail-fast: false so all legs report."""
    text = _workflow_text()
    assert "fail-fast: false" in text, (
        "python-skill matrix should declare `fail-fast: false` so the "
        "divergence-summary aggregator sees every leg"
    )


def test_python_skill_include_overrides_are_in_skill_axis():
    """REQ-CI-040: override-carrying skills are full-coverage entries (no
    os restriction), so their overrides apply on every OS."""
    entries = {e["skill"]: e for e in _matrix_config()["skills"]}
    for skill in ("book-compose", "neurosym-forge"):
        entry = entries[skill]
        assert entry.get("ci") != "none", f"{skill} must be runnable"
        assert "os" not in entry, (
            f"{skill} must inherit the full default OS axis; an os override "
            "would silently drop matrix legs"
        )


def test_coverage_gap_skills_have_smoke_legs():
    """P2-matrix-coverage-gaps: scrapling-fetch + syntopical-metabook are
    covered by an install+import smoke leg, closing the zero-CI-signal gap
    on the highest supply-chain-risk skills."""
    entries = {e["skill"]: e for e in _matrix_config()["skills"]}
    for skill in ("scrapling-fetch", "syntopical-metabook"):
        assert entries[skill].get("smoke") == "import", (
            f"{skill} must be a `smoke: import` entry"
        )


# ---------- REQ-CI-041 ----------


def test_cargo_test_job_exists():
    """REQ-CI-041: a cargo-test job (Linux + macOS) is declared; toolchain
    and z3 come from the flake's rust shell, not apt/brew/rustup."""
    text = _workflow_text()
    assert "cargo-test:" in text or "cargo test" in text, (
        "no cargo-test job declared"
    )
    assert "nix develop .#rust" in text, (
        "cargo-test must take its toolchain + z3 from the flake's rust shell"
    )
    assert "brew install z3" not in text, (
        "apt/brew z3 installs were retired by nix-consolidation PR 3"
    )


def test_cargo_test_skips_windows():
    """REQ-CI-041: cargo-test matrix must NOT include windows-2022."""
    text = _workflow_text()
    # Walk the cargo-test job block and confirm windows-2022 is not in its
    # matrix.os axis. The simplest robust check: the only `windows-2022`
    # mention is inside the python-skill-matrix block (which appears
    # before cargo-test in the file).
    lines = text.splitlines()
    in_cargo_test = False
    cargo_test_block: list[str] = []
    for line in lines:
        if line.startswith("  cargo-test:"):
            in_cargo_test = True
            continue
        if in_cargo_test:
            # New top-level job (2-space indent) ends the cargo-test block
            if line and not line.startswith("    ") and not line.startswith("      ") and not line.startswith(" "):
                break
            if line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(":"):
                # Sibling job key like `  ci-divergence-summary:`
                break
            cargo_test_block.append(line)
    cargo_test_text = "\n".join(cargo_test_block)
    assert "windows-2022" not in cargo_test_text, (
        "cargo-test must not enumerate windows-2022 — Windows cargo is "
        "intentionally skipped per REQ-CI-041 / ci-platforms.md"
    )


# ---------- REQ-CI-042 ----------


def test_divergence_summary_job_exists():
    """REQ-CI-042: ci-divergence-summary aggregator emits to STEP_SUMMARY."""
    text = _workflow_text()
    assert "ci-divergence-summary" in text, (
        "no `ci-divergence-summary` aggregator job declared"
    )
    assert "GITHUB_STEP_SUMMARY" in text, (
        "divergence summary must emit to $GITHUB_STEP_SUMMARY"
    )
    assert "if: always()" in text, (
        "aggregator must run `if: always()` so it surfaces on red runs"
    )


def test_required_depends_on_new_jobs():
    """REQ-CI-042: `required` aggregator depends on the new jobs."""
    text = _workflow_text()
    # The required job's `needs:` block lists cargo-test + ci-divergence-summary
    # alongside the pre-existing python-skill-matrix + preflight.
    for needed in (
        "preflight",
        "python-skill-matrix",
        "cargo-test",
        "ci-divergence-summary",
    ):
        assert f"- {needed}" in text, (
            f"`required` job should depend on `{needed}`"
        )


# ---------- REQ-CI-043 ----------


def test_flake_declares_supported_systems_constant():
    """REQ-CI-043: flake.nix names the supported systems explicitly."""
    assert FLAKE.exists(), f"flake.nix not found at {FLAKE}"
    text = FLAKE.read_text(encoding="utf-8")
    for system in ("x86_64-linux", "aarch64-darwin", "x86_64-darwin"):
        assert system in text, f"flake.nix missing system `{system}`"
    # Either named constant form is acceptable; we check for the
    # forAllSystems = nixpkgs.lib.genAttrs ... idiom from the spec.
    assert "genAttrs" in text or "supportedSystems" in text, (
        "flake.nix should name the supported systems via `genAttrs` or "
        "a `supportedSystems` constant for greppability"
    )


# ---------- REQ-CI-044 ----------


def test_ci_platforms_doc_exists():
    """REQ-CI-044: docs/operations/ci-platforms.md exists."""
    assert CI_PLATFORMS_DOC.exists(), (
        f"runbook not found at {CI_PLATFORMS_DOC}"
    )


def test_ci_platforms_doc_mentions_libz3_per_os():
    """REQ-CI-044: runbook covers libz3 install per OS."""
    text = CI_PLATFORMS_DOC.read_text(encoding="utf-8").lower()
    assert "libz3" in text, "runbook must mention libz3"
    assert "brew install z3" in text, "runbook must mention `brew install z3`"
    assert "libz3-dev" in text, "runbook must mention `libz3-dev` (apt)"


def test_ci_platforms_doc_documents_windows_skip():
    """REQ-CI-044: runbook documents why Windows cargo is skipped."""
    text = CI_PLATFORMS_DOC.read_text(encoding="utf-8").lower()
    assert "windows" in text, "runbook must mention windows"
    assert "skip" in text or "unsupported" in text or "out of scope" in text, (
        "runbook must explain that Windows cargo is skipped/unsupported"
    )


def test_ci_platforms_doc_includes_wsl_fallback():
    """REQ-CI-044: runbook documents the WSL fallback recipe."""
    text = CI_PLATFORMS_DOC.read_text(encoding="utf-8").lower()
    assert "wsl" in text, "runbook must mention WSL"
    # The fallback should mention installing libz3-dev inside WSL Ubuntu.
    assert "ubuntu" in text, "runbook should reference Ubuntu (WSL distro)"


def test_ci_platforms_doc_mentions_act():
    """REQ-CI-044: runbook explains local matrix testing via act."""
    text = CI_PLATFORMS_DOC.read_text(encoding="utf-8").lower()
    assert "act" in text, "runbook should mention nektos/act for local testing"


# ---------- audit: dependabot coverage (findings #1, #3) ----------


def test_dependabot_covers_osmotic_pressure_cargo():
    """#1 dependabot-missing-osmotic-cargo: osmotic_pressure rust crate watched."""
    text = _dependabot_text()
    assert "/verifiers/osmotic_pressure/rust-verifier" in text, (
        "dependabot must have a cargo entry for "
        "/verifiers/osmotic_pressure/rust-verifier"
    )


def test_dependabot_covers_every_cargo_verifier():
    """#1: every rust-verifier crate is watched by dependabot."""
    text = _dependabot_text()
    crates = sorted(
        p.parent for p in (REPO_ROOT / "verifiers").glob("*/rust-verifier/Cargo.toml")
    )
    for crate in crates:
        rel = "/" + crate.relative_to(REPO_ROOT).as_posix()
        assert rel in text, f"dependabot missing cargo entry for {rel}"


def test_dependabot_covers_every_pip_skill():
    """#3 dependabot-missing-skill-pip-dirs: every skill pyproject is watched."""
    text = _dependabot_text()
    skills = sorted(
        p.parent for p in (REPO_ROOT / "skills").glob("*/pyproject.toml")
    )
    for skill in skills:
        rel = "/" + skill.relative_to(REPO_ROOT).as_posix()
        assert rel in text, f"dependabot missing pip entry for {rel}"


# ---------- audit: ci-budget workflow (findings #2, #4, #5) ----------


def test_budget_post_step_never_consumes_missing_file():
    """#2 budget-missing-comment-file: no-green-runs path must not break the
    post-comment step. Either a fallback comment.md is written before the
    early exit, or the post step is guarded by a file-existence check."""
    text = _budget_text()
    # The no-green-runs branch is the text from the diagnostic print up to its
    # early exit. A fallback comment.md must be written *within* that branch
    # (before the exit) — not in the later populated-window block.
    no_green_branch = text.split("no green runs in window", 1)[1].split(
        "SystemExit(0)", 1
    )[0]
    writes_fallback = "comment.md" in no_green_branch
    post_guarded = "hashFiles('comment.md')" in text or "test -f comment.md" in text
    assert writes_fallback or post_guarded, (
        "no-green-runs branch must write a fallback comment.md (before the "
        "early exit) OR the post step must guard on comment.md existence; "
        "otherwise `gh pr comment --body-file comment.md` fails with no file"
    )


def test_budget_metric_labeled_turnaround_not_walltime():
    """#4 ci-budget-window-conflates-queue-time: the metric is updatedAt-createdAt
    (turnaround, includes queue wait), so it must not be labeled 'wall-time'."""
    text = _budget_text()
    # The duration is still derived from createdAt..updatedAt — confirm we did
    # not silently change the data source out from under the label.
    derives_from_created = "createdAt" in text and "updatedAt" in text
    if derives_from_created and "run_started_at" not in text:
        assert "wall-time" not in text and "wall time" not in text.lower(), (
            "metric derived from updatedAt-createdAt includes queue/wait time; "
            "do not label it 'wall-time' — call it 'turnaround time'"
        )
        assert "turnaround" in text.lower(), (
            "rename the queue-inclusive metric to 'turnaround time'"
        )


def test_budget_enforces_or_documents_advisory():
    """#5 budget-advisory-only: an over-budget run must either fail the job
    (a nonzero exit gated on the budget), or the workflow must explicitly
    document that the check is advisory-only."""
    text = _budget_text()
    enforces = "SystemExit(1)" in text or "sys.exit(1)" in text or "exit 1" in text
    documents_advisory = "advisory" in text.lower()
    assert enforces or documents_advisory, (
        "ci-budget computes `ok` but never acts on it: add an over-budget "
        "nonzero exit to gate, or document the check as advisory-only"
    )


# ---------- model-cache hardening (REQ-CI-047) + budget triggers (REQ-CI-048) ----------


def test_model_caches_save_on_warm_success_not_post_job():
    """REQ-CI-047: setup-models uses explicit cache/restore + cache/save so a
    warmed model survives later step failures (the combined actions/cache
    post-job save is skipped on job failure — the 2026-06-04 Windows
    neurosym death spiral)."""
    assert SETUP_MODELS.exists(), f"composite not found at {SETUP_MODELS}"
    text = SETUP_MODELS.read_text(encoding="utf-8")
    assert "actions/cache/restore@" in text, "setup-models must use cache/restore"
    assert "actions/cache/save@" in text, "setup-models must use explicit cache/save"
    assert "actions/cache@" not in text.replace(
        "actions/cache/restore@", ""
    ).replace("actions/cache/save@", ""), (
        "setup-models must not use the combined actions/cache (post-job save "
        "is skipped on job failure)"
    )


def test_python_matrix_uses_setup_models_composite():
    """REQ-CI-047: the matrix job consumes the composite, not inline steps."""
    text = _workflow_text()
    assert "./.github/actions/setup-models" in text


def test_budget_triggers_labeled_only():
    """REQ-CI-048: ci-budget must not trigger on opened/synchronize — the
    label gate made those runs permanent skipped-phantom noise (4-6 per PR
    push)."""
    text = _budget_text()
    on_block = text.split("\njobs:", 1)[0]
    assert "labeled" in on_block, "ci-budget must keep the labeled trigger"
    for noisy in ("opened", "synchronize"):
        assert noisy not in on_block, (
            f"ci-budget pull_request trigger must not include {noisy!r}"
        )


# ---------- audit: ci divergence summary (finding #7) ----------


def test_divergence_table_not_labeled_per_os():
    """#7 divergence-summary-misreports-per-os: the result is a matrix-aggregate
    scalar fanned identically across the OS columns, so the table must not be
    headed with per-OS column labels that imply per-leg diagnosis."""
    text = _workflow_text()
    summary = text.split("ci-divergence-summary:", 1)[1].split("\n  required:", 1)[0]
    # The python-skill / cargo-test rows derive every column from one scalar
    # (needs.<job>.result), so a per-OS header is a false promise. After the
    # fix the table headers must not be the bare OS triplet.
    assert "| Linux | macOS | Windows |" not in summary, (
        "divergence table headers `Linux | macOS | Windows` imply per-OS data, "
        "but the values come from a single aggregate result scalar; drop the "
        "per-OS column headers (the data is matrix-aggregate, not per-leg)"
    )
