import subprocess
import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_AUDIT_ROOT = _REPO_ROOT / "tools" / "russellian-style-audit"


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
