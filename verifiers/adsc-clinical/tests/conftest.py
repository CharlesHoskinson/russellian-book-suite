"""Shared pytest fixtures for verifiers/adsc-clinical/."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_ROOT.parent.parent

# Make the project's `scripts.` namespace importable from the tests.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


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
