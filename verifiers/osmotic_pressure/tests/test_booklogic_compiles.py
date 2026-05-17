"""BookLogic source compiles cleanly via the CLJS expander.

Each test runs the nbb-driven compiler entrypoint
(`nbb -m osmotic_pressure.booklogic <project-root>`) against the project's
rules/booklogic/ directory and asserts exit code 0. The compiler enforces
the structural validation rules (defsort/defpredicate/deflift/defconstraint
shapes; predicate sort references; lift -> predicate references; tolerance
on ~=).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


def _nbb_cmd() -> str | None:
    """Return the nbb executable name if available, or None."""
    for name in ("nbb", "nbb.cmd"):
        if shutil.which(name) is not None:
            return name
    return None


pytestmark = pytest.mark.skipif(_nbb_cmd() is None,
                                reason="nbb not on PATH; CI installs it")


def _run_compiler(project_root: Path) -> subprocess.CompletedProcess:
    """Invoke the CLJS booklogic compiler on the project root."""
    import sys
    nbb = _nbb_cmd() or "nbb"
    # On Windows, .cmd wrappers require shell=True to be executable via subprocess.
    use_shell = sys.platform == "win32"
    return subprocess.run(
        [nbb, "-m", "osmotic_pressure.booklogic", str(project_root)],
        cwd=str(project_root),
        check=False,
        capture_output=True,
        text=True,
        shell=use_shell,
    )


def test_sorts_compiles(project_root: Path) -> None:
    """REQ-OSMOTIC-001: BookLogic sorts compile cleanly."""
    result = _run_compiler(project_root)
    assert result.returncode == 0, (
        f"compiler failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "compiled" in result.stdout
    assert "1 sorts" in result.stdout


def test_predicates_compile(project_root: Path) -> None:
    """REQ-OSMOTIC-010: Four defpredicate forms compile cleanly."""
    result = _run_compiler(project_root)
    assert result.returncode == 0, (
        f"compiler failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "4 predicates" in result.stdout


def test_lifts_compile(project_root: Path) -> None:
    """REQ-OSMOTIC-011: Four deflift forms compile cleanly."""
    result = _run_compiler(project_root)
    assert result.returncode == 0, (
        f"compiler failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "4 lifts" in result.stdout


def test_constraint_compiler_accepts(project_root: Path) -> None:
    """REQ-OSMOTIC-013: Compiler exits 0 with the constraint declared."""
    result = _run_compiler(project_root)
    assert result.returncode == 0, (
        f"compiler failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "1 constraints" in result.stdout


def test_constraint_codegen_lands_in_axioms_rs(project_root: Path) -> None:
    """REQ-OSMOTIC-030: axioms.rs carries the constraint name and tolerance literal.

    Runs the compiler then reads axioms.rs. Marked xfail until Phase 4
    regenerates axioms.rs from the BookLogic source.
    """
    _run_compiler(project_root)
    axioms = (project_root / "rust-verifier" / "src" / "axioms.rs").read_text(
        encoding="utf-8"
    )
    assert "C001-vant-hoff" in axioms or "C001_vant_hoff" in axioms
    assert "0.03" in axioms
