"""Tests for synthesize_findings."""
from __future__ import annotations

import pytest

from scripts.synthesize_findings import (
    _parse_line_range,
    _extract_first_quoted_snippet,
    _locate_snippet_in_chapter,
)


def test_parse_line_range_single_line():
    """'line 14' parses to (14, 14)."""
    assert _parse_line_range("line 14") == (14, 14)


def test_parse_line_range_range_with_dash():
    """'lines 14-22' parses to (14, 22)."""
    assert _parse_line_range("lines 14-22") == (14, 22)


def test_parse_line_range_range_with_en_dash():
    """'lines 14–22' (en-dash) parses to (14, 22)."""
    assert _parse_line_range("lines 14–22") == (14, 22)


def test_parse_line_range_no_match_returns_none():
    """Text without a line ref returns None."""
    assert _parse_line_range("no line reference here") is None


def test_parse_line_range_finds_first_in_longer_text():
    """First line ref in a longer text wins."""
    assert _parse_line_range("In lines 5-8 the issue appears; also at line 17") == (5, 8)


from scripts.synthesize_findings import _tag_themes


def test_tag_themes_listicle():
    assert "listicle" in _tag_themes("Listicle abstract. Cut the roadmap.")


def test_tag_themes_mechanical_parallel():
    assert "mechanical-parallel" in _tag_themes(
        "Mechanical parallel structure. Four consecutive sentences."
    )


def test_tag_themes_em_dash():
    assert "em-dash-overuse" in _tag_themes("Em dash overuse in the opening sentence.")


def test_tag_themes_formulaic_template():
    assert "formulaic-template" in _tag_themes(
        "Formulaic. It is a template, not writing."
    )


def test_tag_themes_no_match_returns_empty():
    assert _tag_themes("a generic comment with no flagged pattern") == set()


def test_tag_themes_multiple_tags():
    tags = _tag_themes("Listicle abstract with mechanical parallel structure")
    assert "listicle" in tags
    assert "mechanical-parallel" in tags


from scripts.synthesize_findings import (
    Finding,
    cluster_findings,
    render_instructions_markdown,
    parse_panel_summary,
)


def test_cluster_findings_overlapping_ranges_merge():
    findings = [
        Finding("gottlieb", "critical", "lines 14-20 listicle abstract", (14, 20)),
        Finding("ai-slop-detector", "critical", "lines 18-22 mechanical parallel", (18, 22)),
    ]
    clusters = cluster_findings(findings)
    assert len(clusters) == 1
    assert clusters[0].line_start == 14
    assert clusters[0].line_end == 22
    assert clusters[0].distinct_personas == {"gottlieb", "ai-slop-detector"}


def test_cluster_findings_distant_ranges_separate():
    findings = [
        Finding("gottlieb", "critical", "line 14 issue", (14, 14)),
        Finding("ai-slop-detector", "critical", "line 200 issue", (200, 200)),
    ]
    clusters = cluster_findings(findings)
    assert len(clusters) == 2


def test_cluster_findings_within_5_lines_merge():
    findings = [
        Finding("gottlieb", "critical", "line 10 a", (10, 10)),
        Finding("ai-slop-detector", "critical", "line 14 b", (14, 14)),
    ]
    clusters = cluster_findings(findings)
    assert len(clusters) == 1


def test_cluster_findings_no_line_range_dropped():
    findings = [
        Finding("gottlieb", "critical", "vague comment", None),
        Finding("ai-slop-detector", "critical", "line 14 specific", (14, 14)),
    ]
    clusters = cluster_findings(findings)
    assert len(clusters) == 1
    assert clusters[0].findings[0].persona_id == "ai-slop-detector"


def test_render_instructions_markdown_orders_by_severity_then_personas():
    clusters_list = [
        cluster_findings([Finding("lay-reader", "important", "line 50 issue", (50, 50))])[0],
        cluster_findings([Finding("gottlieb", "critical", "line 100 issue", (100, 100))])[0],
        cluster_findings([
            Finding("gottlieb", "critical", "line 10 listicle abstract", (10, 10)),
            Finding("ai-slop-detector", "critical", "line 14 listicle abstract", (14, 14)),
        ])[0],
    ]
    md = render_instructions_markdown("ch-01", clusters_list)
    first_cluster_idx = md.find("## Cluster")
    rest = md[first_cluster_idx:]
    second_cluster_idx = rest.find("## Cluster", 1)
    first_block = rest[:second_cluster_idx]
    assert "gottlieb" in first_block and "ai-slop-detector" in first_block


def test_render_instructions_markdown_excludes_minor_clusters():
    clusters_list = cluster_findings([
        Finding("gottlieb", "minor", "line 10 polish", (10, 10)),
    ])
    md = render_instructions_markdown("ch-01", clusters_list)
    assert "no clusters" in md.lower() or "Minor" not in md


def test_parse_panel_summary_extracts_findings_per_persona(tmp_path):
    sample = '''# Persona Review - ch-01

## Severity counts
- Critical: 2

## Aggregated critical findings
- gottlieb: lines 14-22 mechanical parallel structure
- ai-slop-detector: line 30 listicle abstract

## Aggregated important findings
- lay-reader: line 50 jargon density

## Aggregated minor findings
_(none)_
'''
    p = tmp_path / "panel-summary.md"
    p.write_text(sample, encoding="utf-8")
    findings = parse_panel_summary(p)
    assert len(findings) == 3
    severities = [f.severity for f in findings]
    assert severities.count("critical") == 2
    assert severities.count("important") == 1


# ---------------------------------------------------------------------------
# New tests: Enhancement 1 (snippet extraction & location) + Enhancement 2
# ---------------------------------------------------------------------------


def test_extract_first_quoted_snippet_double_quotes():
    assert _extract_first_quoted_snippet('finding: "the cardano case" is a problem') == "the cardano case"


def test_extract_first_quoted_snippet_curly_quotes():
    assert _extract_first_quoted_snippet('finding: “the cardano case” is a problem') == "the cardano case"


def test_extract_first_quoted_snippet_too_short_ignored():
    """Snippets <8 chars are skipped (avoid false positives on "X" tokens)."""
    assert _extract_first_quoted_snippet('an "x" thing') is None


def test_locate_snippet_in_chapter_exact_match(tmp_path):
    chapter_lines = [
        "Line one prose.",
        "This is the Cardano case in detail.",
        "Line three.",
    ]
    assert _locate_snippet_in_chapter("the Cardano case", chapter_lines) == (2, 2)


def test_locate_snippet_in_chapter_no_match(tmp_path):
    chapter_lines = ["Line one.", "Line two."]
    assert _locate_snippet_in_chapter("absent text", chapter_lines) is None


def test_cluster_findings_uses_quoted_snippet_when_no_line_range():
    """A finding with no line ref but a locatable snippet gets a line_range injected."""
    chapter_text = "Line 1.\nThis is the Cardano case in detail.\nLine 3.\n"
    findings = [
        Finding("gottlieb", "critical",
                'listicle abstract: "the Cardano case" should be argued', None),
    ]
    clusters, unanchored = cluster_findings(findings, chapter_text=chapter_text)
    assert len(clusters) == 1
    assert clusters[0].findings[0].line_range == (2, 2)
    assert unanchored == []


def test_cluster_findings_routes_truly_unanchored_to_unanchored_list():
    """A Critical/Important finding with neither line ref nor locatable snippet -> unanchored."""
    chapter_text = "Line 1.\nLine 2.\n"
    findings = [
        Finding("gottlieb", "critical", "vague comment with no anchor", None),
        Finding("ai-slop-detector", "minor", "another vague comment", None),  # Minor: dropped, not unanchored
    ]
    clusters, unanchored = cluster_findings(findings, chapter_text=chapter_text)
    assert clusters == []
    assert len(unanchored) == 1
    assert unanchored[0].persona_id == "gottlieb"


def test_render_instructions_markdown_emits_unanchored_section():
    """Unanchored findings appear under '## Unanchored findings' heading."""
    chapter_text = "Line 1.\nLine 2.\n"
    findings = [
        Finding("gottlieb", "critical", "vague comment", None),
    ]
    clusters, unanchored = cluster_findings(findings, chapter_text=chapter_text)
    md = render_instructions_markdown("ch-01", clusters, unanchored)
    assert "## Unanchored findings" in md
    assert "gottlieb" in md
    assert "vague comment" in md
