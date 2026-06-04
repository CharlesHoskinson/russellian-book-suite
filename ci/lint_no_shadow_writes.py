"""
Pytest plugin: NFR-5 — no shadow writes to canonical workspace directories.

Intercepts the write surface that syntopical-metabook actually uses — builtins.open,
pathlib.Path.open / Path.write_text / Path.write_bytes, and os.open — in
write/append/create modes and raises AssertionError if the target path falls under a
forbidden workspace subdirectory (raw/, claims/, wiki/, or graph/) while any frame
from syntopical-metabook is on the call stack.

This is a TEST-TIME guard only: the monkeypatches are installed by an autouse pytest
fixture and torn down at the end of each test, so the interception is active solely
inside the pytest session. It catches a forbidden write only when a test drives the
real write path while a syntopical-metabook frame is on the stack. It is not a runtime
enforcement boundary; the ledger-ownership invariant (CLAUDE.md) must additionally be
upheld by code organisation. See ci/test_no_shadow_writes.py for tests that drive the
metabook write surface through the guard to prove it fires.

Load via:  pytest -p ci.lint_no_shadow_writes
The conftest.py in ci/ can also register it automatically for the ci/ test suite.
"""
from __future__ import annotations

import builtins
import inspect
import os
import pytest
from pathlib import Path

_FORBIDDEN_DIRS = {"raw", "claims", "wiki", "graph"}
_GUARD_FRAMES = ("syntopical_metabook", "syntopical-metabook")
# A workspace root is marked by a top-level CLAUDE.md (the workspace marker, per
# the repo conventions in CLAUDE.md). Forbidden subdirs are only forbidden when
# they sit directly under such a root.
_WORKSPACE_MARKER = "CLAUDE.md"

_real_open = builtins.open
_real_path_open = Path.open
_real_path_write_text = Path.write_text
_real_path_write_bytes = Path.write_bytes
_real_os_open = os.open


def _is_write_mode(mode: str) -> bool:
    return any(c in mode for c in ("w", "a", "x", "+"))


def _is_write_flags(flags: int) -> bool:
    return bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC))


def _path_under_workspace_subdir(path) -> bool:
    """True iff *path* lies under <workspace_root>/<forbidden_subdir>/...

    The forbidden subdir name must be a *direct child of a workspace root* — a
    directory containing the CLAUDE.md workspace marker. This anchors the check
    to a real workspace layout rather than matching the bare directory name at
    any depth of the absolute path (which would falsely flag e.g. a CI checkout
    or temp dir that merely contains a segment named "graph").
    """
    try:
        resolved = Path(path).resolve()
    except Exception:
        return False
    # Walk ancestors looking for a `<root>/<forbidden>` boundary where `<root>`
    # is a workspace root (has the CLAUDE.md marker).
    for ancestor in resolved.parents:
        if ancestor.name in _FORBIDDEN_DIRS:
            root = ancestor.parent
            try:
                if (root / _WORKSPACE_MARKER).exists():
                    return True
            except Exception:
                continue
    return False


def _metabook_in_stack() -> bool:
    for frame in inspect.stack():
        filename = frame.filename.lower()
        if any(g in filename for g in _GUARD_FRAMES):
            return True
    return False


def _violation(target) -> AssertionError:
    return AssertionError(
        f"NFR-5 violated: syntopical-metabook wrote to {target} (forbidden subdir)"
    )


def _guarded_open(file, mode="r", *args, **kwargs):
    if isinstance(file, (str, Path)) and _is_write_mode(str(mode)):
        if _path_under_workspace_subdir(file) and _metabook_in_stack():
            raise _violation(file)
    return _real_open(file, mode, *args, **kwargs)


def _guarded_path_open(self, mode="r", *args, **kwargs):
    if _is_write_mode(str(mode)):
        if _path_under_workspace_subdir(self) and _metabook_in_stack():
            raise _violation(self)
    return _real_path_open(self, mode, *args, **kwargs)


def _guarded_path_write_text(self, *args, **kwargs):
    if _path_under_workspace_subdir(self) and _metabook_in_stack():
        raise _violation(self)
    return _real_path_write_text(self, *args, **kwargs)


def _guarded_path_write_bytes(self, *args, **kwargs):
    if _path_under_workspace_subdir(self) and _metabook_in_stack():
        raise _violation(self)
    return _real_path_write_bytes(self, *args, **kwargs)


def _guarded_os_open(path, flags, *args, **kwargs):
    if isinstance(path, (str, bytes, os.PathLike)) and _is_write_flags(int(flags)):
        if _path_under_workspace_subdir(os.fsdecode(path)) and _metabook_in_stack():
            raise _violation(path)
    return _real_os_open(path, flags, *args, **kwargs)


@pytest.fixture(autouse=True)
def _no_shadow_writes(monkeypatch):
    """Autouse fixture: patches the metabook write surface for every test.

    Test-time only — monkeypatch restores the originals at teardown, so this has
    no effect outside the pytest session.
    """
    monkeypatch.setattr(builtins, "open", _guarded_open)
    monkeypatch.setattr(Path, "open", _guarded_path_open)
    monkeypatch.setattr(Path, "write_text", _guarded_path_write_text)
    monkeypatch.setattr(Path, "write_bytes", _guarded_path_write_bytes)
    monkeypatch.setattr(os, "open", _guarded_os_open)
    yield
