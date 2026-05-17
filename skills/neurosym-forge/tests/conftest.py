"""Shared pytest fixtures for neurosym-forge tests."""
from __future__ import annotations

from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def skill_root() -> Path:
    """Absolute path to the skill root (skills/neurosym-forge/)."""
    return SKILL_ROOT


@pytest.fixture()
def assets_dir(skill_root: Path) -> Path:
    return skill_root / "assets"


@pytest.fixture()
def schemas_dir(assets_dir: Path) -> Path:
    return assets_dir / "schemas"


@pytest.fixture()
def fixtures_dir(skill_root: Path) -> Path:
    return skill_root / "tests" / "fixtures"


@pytest.fixture()
def project_template_dir(assets_dir: Path) -> Path:
    return assets_dir / "project-template"


@pytest.fixture()
def tmp_project_root(tmp_path: Path) -> Path:
    """Where scaffold_project writes its output during tests."""
    root = tmp_path / "verifiers" / "demo"
    return root


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
