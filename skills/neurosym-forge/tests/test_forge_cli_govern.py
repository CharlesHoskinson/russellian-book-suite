"""forge govern subcommand group routing."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
FORGE = ROOT / "neurosym-forge" / "scripts" / "forge_cli.py"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(FORGE)] + args,
        capture_output=True, text=True, check=False,
    )


def test_govern_help_lists_subcommands():
    out = _run(["govern", "--help"])
    assert out.returncode == 0
    for sub in ("build", "report"):
        assert sub in out.stdout


def test_govern_build_requires_workspace_arg():
    out = _run(["govern", "build"])
    assert out.returncode != 0
    assert "WORKSPACE" in out.stderr or "PROJECT_ROOT" in out.stderr or "Missing argument" in out.stderr
