"""BookLogic source compiles cleanly via the CLJS expander.

Mirrors verifiers/osmotic_pressure/tests/test_booklogic_compiles.py. The
tests skip when nbb is not on PATH (local Windows-without-WSL case);
CI installs nbb and runs the full compile.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def _nbb_cmd() -> str | None:
    for name in ("nbb", "nbb.cmd"):
        if shutil.which(name) is not None:
            return name
    return None


pytestmark = pytest.mark.skipif(_nbb_cmd() is None,
                                reason="nbb not on PATH; CI installs it")


def _run_compiler(project_root: Path) -> subprocess.CompletedProcess:
    nbb = _nbb_cmd() or "nbb"
    use_shell = sys.platform == "win32"
    return subprocess.run(
        [nbb, "-m", "epidemiology.booklogic", str(project_root)],
        cwd=str(project_root),
        check=False,
        capture_output=True,
        text=True,
        shell=use_shell,
    )


def test_sorts_compiles(project_root: Path) -> None:
    """REQ-EVAL-040: epidemiology sorts compile cleanly (2 sorts)."""
    result = _run_compiler(project_root)
    assert result.returncode == 0, (
        f"compiler failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "compiled" in result.stdout
    assert "2 sorts" in result.stdout


def test_predicates_compile(project_root: Path) -> None:
    """REQ-EVAL-040: three defpredicate forms compile cleanly."""
    result = _run_compiler(project_root)
    assert result.returncode == 0
    assert "3 predicates" in result.stdout


def test_lifts_compile(project_root: Path) -> None:
    """REQ-EVAL-041: three deflift forms compile cleanly."""
    result = _run_compiler(project_root)
    assert result.returncode == 0
    assert "3 lifts" in result.stdout


def test_constraints_compile(project_root: Path) -> None:
    """REQ-EVAL-042: two defconstraint forms compile cleanly."""
    result = _run_compiler(project_root)
    assert result.returncode == 0
    assert "2 constraints" in result.stdout


def test_constraints_land_in_axioms_rs(project_root: Path) -> None:
    """REQ-EVAL-043: axioms.rs carries both constraint names + tolerances."""
    _run_compiler(project_root)
    axioms = (project_root / "rust-verifier" / "src" / "axioms.rs").read_text(
        encoding="utf-8"
    )
    assert "C001-herd-immunity" in axioms or "C001_herd_immunity" in axioms
    assert "C002-threshold-formula" in axioms or "C002_threshold_formula" in axioms
    assert "60000" in axioms  # 0.06 tolerance, codegen rational
    assert "50000" in axioms  # 0.05 tolerance, codegen rational
