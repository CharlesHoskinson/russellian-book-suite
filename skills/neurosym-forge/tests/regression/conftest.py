"""Shared fixtures for the sprint-5 regression suite.

Each regression test:
  1. Bakes a fresh project via scaffold_project()
  2. Mutates one file to re-introduce the sprint-5 bug
  3. Asserts the appropriate gate fails on `make ci`
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_ROOT = REPO_ROOT / "skills" / "neurosym-forge"


@pytest.fixture()
def fresh_bake(tmp_path: Path) -> Callable[[str], Path]:
    """Return a callable that bakes a fresh project and returns its path."""
    import sys
    sys.path.insert(0, str(SKILL_ROOT))
    from scripts.scaffold_project import scaffold_project  # type: ignore

    def _bake(slug: str = "regr_test") -> Path:
        out_dir = tmp_path / slug
        scaffold_project(
            project_name="Regression",
            project_slug=slug,
            out_dir=out_dir,
            skill_root=SKILL_ROOT,
        )
        # Drop in smoke rules
        src_rules = SKILL_ROOT / "tests" / "fixtures" / "bake-smoke-rules"
        dst_rules = out_dir / "rules" / "booklogic"
        dst_rules.mkdir(parents=True, exist_ok=True)
        for f in src_rules.iterdir():
            shutil.copy(f, dst_rules / f.name)
        return out_dir

    return _bake


def run_make_ci(project_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", "ci"], cwd=project_dir,
        capture_output=True, text=True, check=False,
    )
