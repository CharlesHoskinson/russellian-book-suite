"""
Pytest plugin: NFR-5 — no shadow writes to canonical workspace directories.

Intercepts builtins.open in write/append/create modes and raises AssertionError
if the target path falls under a forbidden workspace subdirectory (raw/, claims/,
wiki/, or graph/) while any frame from syntopical-metabook is on the call stack.

Load via:  pytest -p ci.lint_no_shadow_writes
The conftest.py in ci/ can also register it automatically for the ci/ test suite.
"""
from __future__ import annotations

import builtins
import inspect
import pytest
from pathlib import Path

_FORBIDDEN_DIRS = {"raw", "claims", "wiki", "graph"}
_GUARD_FRAMES = ("syntopical_metabook", "syntopical-metabook")

_real_open = builtins.open


def _is_write_mode(mode: str) -> bool:
    return any(c in mode for c in ("w", "a", "x", "+"))


def _path_under_workspace_subdir(path) -> bool:
    try:
        parts = Path(path).resolve().parts
    except Exception:
        return False
    return any(p in _FORBIDDEN_DIRS for p in parts)


def _metabook_in_stack() -> bool:
    for frame in inspect.stack():
        filename = frame.filename.lower()
        if any(g in filename for g in _GUARD_FRAMES):
            return True
    return False


def _guarded_open(file, mode="r", *args, **kwargs):
    if isinstance(file, (str, Path)) and _is_write_mode(str(mode)):
        if _path_under_workspace_subdir(file) and _metabook_in_stack():
            raise AssertionError(
                f"NFR-5 violated: syntopical-metabook wrote to {file} (forbidden subdir)"
            )
    return _real_open(file, mode, *args, **kwargs)


@pytest.fixture(autouse=True)
def _no_shadow_writes(monkeypatch):
    """Autouse fixture: patches builtins.open for every test in the session."""
    monkeypatch.setattr(builtins, "open", _guarded_open)
    yield
