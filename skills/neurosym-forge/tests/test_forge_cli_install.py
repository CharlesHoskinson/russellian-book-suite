"""Entry-point install shape tests (REQ-AUTHOR-046).

The ``pip install -e .`` integration test is gated on running a fresh
venv build, which is heavy for the day-to-day pytest pass; we exercise
the entry-point declaration here at import time and leave the full
fresh-venv install to CI (where the build matrix runs ``pip install -e``
on each supported Python).
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

import importlib.metadata as md
from pathlib import Path

import pytest


SKILL_ROOT = Path(__file__).resolve().parent.parent


def test_pyproject_declares_console_script() -> None:
    """pyproject.toml declares the forge console-script entry point."""
    pyproject = (SKILL_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[project.scripts]" in pyproject
    assert 'forge = "scripts.forge_cli:main"' in pyproject


def test_pyproject_pins_click_dependency() -> None:
    """click is in the runtime dep list (CLI library)."""
    pyproject = (SKILL_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "click>=" in pyproject


def test_main_target_imports_and_is_callable() -> None:
    """The scripts.forge_cli:main target named in [project.scripts] resolves."""
    from scripts import forge_cli

    assert callable(forge_cli.main)
    assert callable(forge_cli.cli)


def test_neurosym_forge_distribution_metadata_if_installed() -> None:
    """If the package is editable-installed, the forge entry point is registered."""
    try:
        dist = md.distribution("neurosym-forge")
    except md.PackageNotFoundError:
        pytest.skip("neurosym-forge not installed; skipping installed-metadata check.")
    entry_points = {ep.name: ep.value for ep in dist.entry_points
                    if ep.group == "console_scripts"}
    assert entry_points.get("forge") == "scripts.forge_cli:main", (
        f"Expected forge entry point, got {entry_points}"
    )
