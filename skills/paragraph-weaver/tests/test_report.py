# tests/test_report.py
from __future__ import annotations

from engine.report import Segment, render_provenance, render_clean


def _segments():
    return [
        Segment(kind="source", text="Snails carry a shell."),
        Segment(kind="bridge", text="This shell is a spiral."),
        Segment(kind="seam", text="The spiral grows."),
    ]


def test_provenance_marks_bridge_and_seam():
    md = render_provenance(_segments())
    assert "<!-- bridge -->" in md
    assert "<!-- seam -->" in md
    assert "Snails carry a shell." in md


def test_clean_has_no_marks():
    md = render_clean(_segments())
    assert "<!--" not in md
    assert md.count("\n\n") == 2  # three segments joined by blank lines
