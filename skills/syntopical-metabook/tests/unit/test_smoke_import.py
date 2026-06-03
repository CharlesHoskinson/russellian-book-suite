"""CI import-smoke regression guard.

The CI smoke leg runs `python -c "import skill_api"` from the skill dir with
only the base package installed — no repo-root sys.path injection, so the
sibling_skills package is unavailable. skill_api's public surface must import
without it (loaders are lazy; they resolve siblings at call time).
"""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]


def test_skill_api_imports_without_sibling_skills():
    env = {**os.environ, "PYTHONPATH": ""}
    probe = subprocess.run(
        [sys.executable, "-c", "import sibling_skills"],
        cwd=SKILL_ROOT, env=env, capture_output=True, text=True,
    )
    if probe.returncode == 0:
        import pytest
        pytest.skip("sibling_skills importable in this interpreter; simulation vacuous")
    result = subprocess.run(
        [sys.executable, "-c", "import skill_api; print(skill_api.API_VERSION)"],
        cwd=SKILL_ROOT, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
