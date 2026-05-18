"""Shared pytest fixtures for verifiers/epidemiology/."""
from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_ROOT.parent.parent


@pytest.fixture()
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture()
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture()
def fixtures_dir() -> Path:
    return PROJECT_ROOT / "fixtures"


@pytest.fixture()
def tmp_work(tmp_path: Path) -> Path:
    work = tmp_path / "work"
    work.mkdir()
    return work
