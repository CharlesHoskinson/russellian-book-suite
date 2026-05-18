"""Smoke tests for the no-shadow-writes pytest plugin (NFR-5).

Full enforcement fires in Phase 6 when syntopical-metabook scripts exist.
Here we verify the plugin helpers behave correctly on synthetic paths.

Invoke via:  ci/.venv/Scripts/python.exe -m pytest ci/test_no_shadow_writes.py -v
"""

from ci.lint_no_shadow_writes import (
    _is_write_mode,
    _path_under_workspace_subdir,
)


def test_is_write_mode_detects_w_a_x_plus():
    assert _is_write_mode("w") is True
    assert _is_write_mode("a") is True
    assert _is_write_mode("x") is True
    assert _is_write_mode("r+") is True
    assert _is_write_mode("rb") is False
    assert _is_write_mode("r") is False


def test_path_under_workspace_subdir(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    target = raw_dir / "f.bin"
    # safe write — we're not in the metabook stack, guard won't trigger
    target.write_bytes(b"")
    assert _path_under_workspace_subdir(target) is True


def test_path_outside_forbidden_subdir(tmp_path):
    other = tmp_path / "other" / "f.txt"
    other.parent.mkdir()
    other.write_text("ok")
    assert _path_under_workspace_subdir(other) is False
