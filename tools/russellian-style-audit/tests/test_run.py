import subprocess
import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_AUDIT_ROOT = _REPO_ROOT / "tools" / "russellian-style-audit"
sys.path.insert(0, str(_AUDIT_ROOT))

from scripts.run import _bundle_root, _samples_exit_code  # noqa: E402


def test_bundle_root_is_batch_scoped():
    """Re-running with a different batch-id must not target the same bundle root —
    finding audit-bundle-path-not-batch-scoped."""
    a = _bundle_root("2026-05-21-001")
    b = _bundle_root("2026-05-29-002")
    assert a != b
    assert "2026-05-21-001" in str(a)
    assert "2026-05-29-002" in str(b)


def test_samples_exit_code_nonzero_on_fail_only_when_strict():
    """A failing sample verdict must produce a nonzero exit only under --strict; the
    default stays 0 so the existing non-gating behaviour is preserved — finding
    audit-exit-ignores-sample-failures."""
    rows_with_fail = [
        {"mode": "technical-exposition", "gating": 0, "advisory": 1, "verdict": "PASS"},
        {"mode": "narrative-editorial", "gating": 3, "advisory": 7, "verdict": "FAIL"},
    ]
    rows_all_pass = [
        {"mode": "technical-exposition", "gating": 0, "advisory": 1, "verdict": "PASS"},
    ]
    assert _samples_exit_code(rows_with_fail, strict=True) != 0
    assert _samples_exit_code(rows_with_fail, strict=False) == 0
    assert _samples_exit_code(rows_all_pass, strict=True) == 0


@pytest.mark.skipif(
    not (_AUDIT_ROOT / ".venv").exists(),
    reason="audit venv not installed; skip integration smoke",
)
def test_run_help_exits_zero():
    venv_python = _AUDIT_ROOT / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")
    completed = subprocess.run(
        [str(venv_python), "-m", "scripts.run", "--help"],
        capture_output=True, text=True, cwd=str(_AUDIT_ROOT),
    )
    assert completed.returncode == 0
    assert "--batch-id" in completed.stdout
    assert "--auto-accept" in completed.stdout
    assert "--skip-expansion" in completed.stdout
