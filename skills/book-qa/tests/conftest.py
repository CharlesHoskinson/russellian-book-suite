"""Shared pytest fixtures for book-qa lint tests.

Each lint test wants a temporary workspace shaped like the real book pipeline:

    <workspace>/
      book/releases/<version>/
        manuscript.md
        manuscript.html       (optional)
        figures/...            (optional asset tree)

`stage_release` copies a chosen fixture markdown (and optional html / asset
files) into that tree and returns (workspace, version) ready for
`lint_artifact`.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

# Make the skill's scripts/ importable as `scripts.lint_artifact`.
SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def stage_release(tmp_path: Path):
    """Return a helper that drops fixture files into a workspace and returns
    (workspace, version)."""

    def _stage(md_name: str,
               html_name: str | None = None,
               assets: list[tuple[str, str]] | None = None,
               version: str = "v0.1.0") -> tuple[Path, str]:
        release = tmp_path / "book" / "releases" / version
        release.mkdir(parents=True, exist_ok=True)
        shutil.copy(FIXTURES / md_name, release / "manuscript.md")
        if html_name is not None:
            shutil.copy(FIXTURES / html_name, release / "manuscript.html")
        if assets:
            for src_rel, dst_rel in assets:
                target = release / dst_rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(FIXTURES / src_rel, target)
        return tmp_path, version

    return _stage
