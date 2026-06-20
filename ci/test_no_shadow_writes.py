"""Tests for the no-shadow-writes pytest plugin (NFR-5).

Covers the pure path/mode helpers, the workspace-root anchoring (no substring
overmatch), and end-to-end enforcement: a write driven through the metabook
write surface (pathlib + builtins) while a syntopical-metabook frame is on the
stack must trip the guard.

This guard is TEST-TIME only — the autouse fixture patches the write surface for
the duration of each test and restores it at teardown. It is not a runtime
enforcement boundary.

Invoke via:  python -m pytest ci/test_no_shadow_writes.py -v   (from the repo root)
"""
import os
from pathlib import Path

import pytest

from ci.lint_no_shadow_writes import (
    _is_write_mode,
    _is_write_flags,
    _path_under_workspace_subdir,
)


def test_is_write_mode_detects_w_a_x_plus():
    assert _is_write_mode("w") is True
    assert _is_write_mode("a") is True
    assert _is_write_mode("x") is True
    assert _is_write_mode("r+") is True
    assert _is_write_mode("rb") is False
    assert _is_write_mode("r") is False


def test_is_write_flags_detects_write_intent():
    assert _is_write_flags(os.O_WRONLY) is True
    assert _is_write_flags(os.O_RDWR) is True
    assert _is_write_flags(os.O_WRONLY | os.O_CREAT | os.O_TRUNC) is True
    assert _is_write_flags(os.O_RDONLY) is False


def _make_workspace(tmp_path: Path) -> Path:
    """A workspace root is marked by a top-level CLAUDE.md."""
    (tmp_path / "CLAUDE.md").write_text("# workspace marker", encoding="utf-8")
    return tmp_path


def test_path_under_workspace_subdir(tmp_path):
    ws = _make_workspace(tmp_path)
    raw_dir = ws / "raw"
    raw_dir.mkdir()
    target = raw_dir / "f.bin"
    assert _path_under_workspace_subdir(target) is True


def test_path_outside_forbidden_subdir(tmp_path):
    ws = _make_workspace(tmp_path)
    other = ws / "other" / "f.txt"
    other.parent.mkdir()
    assert _path_under_workspace_subdir(other) is False


def test_no_overmatch_on_unanchored_forbidden_name(tmp_path):
    """A dir literally named 'graph' that is NOT a workspace subdir (no CLAUDE.md
    marker at its parent) must not be flagged — guards against the substring
    overmatch where any 'graph'/'wiki'/'raw'/'claims' segment at any depth tripped
    the check (e.g. a CI checkout or temp dir named 'graph')."""
    # No CLAUDE.md marker anywhere — this is just an unrelated directory tree.
    target = tmp_path / "graph" / "node_modules" / "f.txt"
    target.parent.mkdir(parents=True)
    assert _path_under_workspace_subdir(target) is False


def test_nested_forbidden_under_non_workspace_not_flagged(tmp_path):
    """`<tmp>/wiki/...` where <tmp> has no CLAUDE.md is not a workspace subdir."""
    target = tmp_path / "wiki" / "page.md"
    target.parent.mkdir()
    assert _path_under_workspace_subdir(target) is False


# --- end-to-end enforcement: the guard must actually fire on the real write
# surface metabook uses (pathlib + builtins), not just builtins.open. These
# tests run with the autouse fixture active and put a syntopical-metabook frame
# on the stack via a helper module whose filename matches _GUARD_FRAMES.

def _drive_write_from_metabook_frame(write_callable):
    """Call write_callable() through a module path containing 'syntopical_metabook'
    so _metabook_in_stack() returns True. We synthesise the frame by exec-ing in a
    code object whose co_filename embeds the guard token."""
    src = "def _w(cb):\n    return cb()\n"
    code = compile(src, "/tmp/syntopical_metabook_synthetic.py", "exec")
    ns: dict = {}
    exec(code, ns)
    return ns["_w"](write_callable)


def test_guard_fires_on_path_write_text(tmp_path):
    ws = _make_workspace(tmp_path)
    (ws / "claims").mkdir()
    target = ws / "claims" / "ledger.jsonl"
    with pytest.raises(AssertionError, match="NFR-5 violated"):
        _drive_write_from_metabook_frame(lambda: target.write_text("x", encoding="utf-8"))


def test_guard_fires_on_path_write_bytes(tmp_path):
    ws = _make_workspace(tmp_path)
    (ws / "raw").mkdir()
    target = ws / "raw" / "f.bin"
    with pytest.raises(AssertionError, match="NFR-5 violated"):
        _drive_write_from_metabook_frame(lambda: target.write_bytes(b"x"))


def test_guard_fires_on_path_open_append(tmp_path):
    ws = _make_workspace(tmp_path)
    (ws / "wiki").mkdir()
    target = ws / "wiki" / "page.md"

    def _do():
        with target.open("a", encoding="utf-8") as f:
            f.write("x")

    with pytest.raises(AssertionError, match="NFR-5 violated"):
        _drive_write_from_metabook_frame(_do)


def test_guard_fires_on_builtins_open(tmp_path):
    ws = _make_workspace(tmp_path)
    (ws / "graph").mkdir()
    target = ws / "graph" / "g.edn"

    def _do():
        with open(target, "w", encoding="utf-8") as f:
            f.write("x")

    with pytest.raises(AssertionError, match="NFR-5 violated"):
        _drive_write_from_metabook_frame(_do)


def test_guard_allows_writes_outside_metabook_stack(tmp_path):
    """Same forbidden target, but no metabook frame on the stack — must be allowed."""
    ws = _make_workspace(tmp_path)
    (ws / "claims").mkdir()
    target = ws / "claims" / "ledger.jsonl"
    target.write_text("ok", encoding="utf-8")  # no exception
    assert target.read_text(encoding="utf-8") == "ok"


def test_guard_allows_non_forbidden_target_from_metabook(tmp_path):
    """A metabook write to a non-forbidden dir must be allowed."""
    ws = _make_workspace(tmp_path)
    (ws / "reports").mkdir()
    target = ws / "reports" / "summary.md"
    _drive_write_from_metabook_frame(lambda: target.write_text("ok", encoding="utf-8"))
    assert target.read_text(encoding="utf-8") == "ok"
