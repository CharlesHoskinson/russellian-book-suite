"""Shared pytest fixtures for verifiers/bermuda/."""
from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture()
def fixtures_dir() -> Path:
    return PROJECT_ROOT / "tests" / "fixtures"


@pytest.fixture()
def tmp_work(tmp_path: Path) -> Path:
    work = tmp_path / "work"
    work.mkdir()
    return work
