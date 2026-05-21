"""forge induce --governance-gate filters via positions.edn."""
from __future__ import annotations
import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
FORGE = ROOT / "neurosym-forge" / "scripts" / "forge_cli.py"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(FORGE)] + args,
        capture_output=True, text=True, check=False,
    )


def test_induce_help_lists_governance_gate_flag():
    out = _run(["induce", "--help"])
    assert "--governance-gate" in out.stdout


def test_induce_with_governance_gate_requires_positions(tmp_path):
    """Without positions.edn, the gate cannot make decisions; surface a clean error or warning."""
    workspace = tmp_path / "ws"
    (workspace / "syntopical").mkdir(parents=True)
    # induce requires rules/booklogic/ to exist before it can reach gate logic
    (workspace / "rules" / "booklogic").mkdir(parents=True)
    out = _run(["induce", str(workspace), "--governance-gate"])
    # Either fail with a clear message OR run and warn about missing positions.
    # We assert the message is present somewhere in the output streams.
    assert "governance" in (out.stdout + out.stderr).lower() or "positions" in (out.stdout + out.stderr).lower()
