from __future__ import annotations

from pathlib import Path

from scripts.render_call_graph import render_call_graph


def test_ascii_contains_phases() -> None:
    out = render_call_graph(project_slug="demo")
    assert "Claude" in out
    assert "ClojureScript" in out
    assert "Rust" in out


def test_ascii_is_pure_ascii() -> None:
    out = render_call_graph(project_slug="demo")
    out.encode("ascii")  # raises on non-ascii
