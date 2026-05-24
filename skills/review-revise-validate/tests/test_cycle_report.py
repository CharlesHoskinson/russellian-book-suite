"""Tests for cycle_report.py — before/after diff of panel summaries."""
from __future__ import annotations

import pytest

from scripts.cycle_report import (
    PanelSummary,
    parse_panel_summary,
    compute_diff,
    render_report_markdown,
)


def test_parse_panel_summary_extracts_verdicts_and_counts(tmp_path):
    sample = """# Persona Review - ch-01

## Severity counts
- Critical: 5
- Important: 3
- Minor: 1

## Per-persona verdicts
- gottlieb: NEEDS_WORK
- ai-slop-detector: APPROVED_WITH_NOTES
"""
    p = tmp_path / "summary.md"
    p.write_text(sample, encoding="utf-8")
    s = parse_panel_summary(p)
    assert s.critical_total == 5
    assert s.important_total == 3
    assert s.minor_total == 1
    assert s.verdicts["gottlieb"] == "NEEDS_WORK"
    assert s.verdicts["ai-slop-detector"] == "APPROVED_WITH_NOTES"


def test_compute_diff_detects_improvement():
    before = PanelSummary(critical_total=5, important_total=3, minor_total=1, verdicts={"gottlieb": "NEEDS_WORK"})
    after = PanelSummary(critical_total=2, important_total=2, minor_total=1, verdicts={"gottlieb": "APPROVED_WITH_NOTES"})
    d = compute_diff(before, after)
    assert d.critical_delta == -3
    assert d.regression is False


def test_compute_diff_detects_regression():
    before = PanelSummary(critical_total=1, important_total=0, minor_total=0, verdicts={})
    after = PanelSummary(critical_total=3, important_total=0, minor_total=0, verdicts={})
    d = compute_diff(before, after)
    assert d.critical_delta == 2
    assert d.regression is True


def test_render_report_markdown_emits_counts_table():
    before = PanelSummary(critical_total=5, important_total=3, minor_total=1, verdicts={})
    after = PanelSummary(critical_total=2, important_total=2, minor_total=1, verdicts={})
    d = compute_diff(before, after)
    md = render_report_markdown(chapter_id="ch-01", before=before, after=after, diff=d)
    # Counts table must contain Critical row with before, after, and (signed delta)
    assert "Critical" in md
    assert " 5 " in md or "| 5" in md
    assert " 2 " in md or "| 2" in md
    assert "(-3)" in md


def test_render_report_markdown_emits_regression_warning_at_top():
    before = PanelSummary(critical_total=0, important_total=0, minor_total=0, verdicts={})
    after = PanelSummary(critical_total=2, important_total=0, minor_total=0, verdicts={})
    d = compute_diff(before, after)
    md = render_report_markdown(chapter_id="ch-01", before=before, after=after, diff=d)
    # Regression block must precede the verdicts section (or anywhere — but must exist at the top)
    regression_idx = md.find("REGRESSION")
    verdicts_idx = md.find("Verdicts")
    assert regression_idx >= 0
    # If Verdicts section exists at all, REGRESSION must come first
    assert verdicts_idx == -1 or regression_idx < verdicts_idx
