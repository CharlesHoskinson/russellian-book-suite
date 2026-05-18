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

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
FLAKE = REPO_ROOT / "flake.nix"
CI_PLATFORMS_DOC = REPO_ROOT / "docs" / "operations" / "ci-platforms.md"


def _workflow_text() -> str:
    assert WORKFLOW.exists(), f"workflow not found at {WORKFLOW}"
    return WORKFLOW.read_text(encoding="utf-8")


# ---------- REQ-CI-040 ----------


def test_python_skill_matrix_has_three_oses():
    """REQ-CI-040: python-skill matrix axis enumerates all three OSes."""
    text = _workflow_text()
    for os_label in ("ubuntu-24.04", "macos-latest", "windows-2022"):
        assert os_label in text, f"workflow missing OS label {os_label}"


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


# ---------- REQ-CI-041 ----------


def test_cargo_test_job_exists():
    """REQ-CI-041: a cargo-test job (Linux + macOS) is declared."""
    text = _workflow_text()
    # Loose check: the job key appears, and the macOS install step is wired.
    assert "cargo-test:" in text or "cargo test" in text, (
        "no cargo-test job declared"
    )
    assert "brew install z3" in text, (
        "cargo-test macOS leg should run `brew install z3`"
    )
    assert "libz3-dev" in text, (
        "cargo-test Linux leg should install libz3-dev via apt"
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
