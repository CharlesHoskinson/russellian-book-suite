"""Tests for ``scripts.forge_cli`` (REQ-AUTHOR-040..046)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts import forge_cli


SUBCOMMANDS = (
    "add-constraint",
    "suggest-lifts",
    "explain-defect",
    "similar",
    "render",
)


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# REQ-AUTHOR-040 — group + 5 subcommands exposed
# ---------------------------------------------------------------------------


def test_all_subcommands_exposed(runner: CliRunner) -> None:
    result = runner.invoke(forge_cli.cli, ["--help"])
    assert result.exit_code == 0, result.output
    for sub in SUBCOMMANDS:
        assert sub in result.output


def test_module_invocation_help_lists_subcommands() -> None:
    """Invoking ``python -m scripts.forge_cli --help`` works (entry-point shape)."""
    skill_root = Path(forge_cli.__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "scripts.forge_cli", "--help"],
        cwd=str(skill_root),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    for sub in SUBCOMMANDS:
        assert sub in result.stdout


def test_each_subcommand_has_help(runner: CliRunner) -> None:
    """Each subcommand exposes non-trivial --help text."""
    for sub in SUBCOMMANDS:
        result = runner.invoke(forge_cli.cli, [sub, "--help"])
        assert result.exit_code == 0, f"{sub}: {result.output}"
        assert "Usage" in result.output
        assert "--help" in result.output


def test_forge_cli_exposes_main_callable() -> None:
    """The entry point declared in pyproject.toml is callable."""
    assert callable(forge_cli.main)
    assert callable(forge_cli.cli)


def test_pyproject_declares_forge_entry_point() -> None:
    skill_root = Path(forge_cli.__file__).resolve().parent.parent
    pyproject = (skill_root / "pyproject.toml").read_text(encoding="utf-8")
    assert "[project.scripts]" in pyproject
    assert 'forge = "scripts.forge_cli:main"' in pyproject
    assert "click" in pyproject
