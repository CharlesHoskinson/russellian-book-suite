"""Footnote-integrity linter: orphaned inline markers and orphaned definitions."""
import pytest

pytestmark = pytest.mark.windows_canary

from scripts.lint_footnotes import find_orphans


def test_balanced_footnotes_clean():
    text = "Body with a cite.[^a] More here.[^b]\n\n[^a]: def a\n[^b]: def b\n"
    assert find_orphans(text) == []


def test_orphan_definition_flagged():
    # [^a] referenced; [^b] defined but never cited inline.
    text = "Body.[^a]\n\n[^a]: def a\n[^b]: def b\n"
    orphans = find_orphans(text)
    assert len(orphans) == 1
    assert orphans[0]["kind"] == "orphan-definition"
    assert orphans[0]["label"] == "b"


def test_orphan_marker_flagged():
    text = "Body.[^a] and then.[^missing]\n\n[^a]: def a\n"
    orphans = find_orphans(text)
    assert len(orphans) == 1
    assert orphans[0]["kind"] == "orphan-marker"
    assert orphans[0]["label"] == "missing"


def test_all_definitions_no_markers_all_orphaned():
    # The ch3 bug: every definition present, zero inline markers.
    text = "Body with no markers at all anywhere.\n\n[^a]: def a\n[^b]: def b\n"
    orphans = find_orphans(text)
    assert {o["label"] for o in orphans} == {"a", "b"}
    assert all(o["kind"] == "orphan-definition" for o in orphans)


def test_reused_marker_single_definition_clean():
    # Same label cited twice inline, defined once (e.g. [^desoto]) is valid.
    text = "One.[^x] Two.[^x]\n\n[^x]: def\n"
    assert find_orphans(text) == []


def test_definition_token_not_counted_as_marker():
    text = "Ref.[^x]\n\n[^x]: the definition body\n"
    assert find_orphans(text) == []


def test_code_fence_ignored():
    text = "Real cite.[^a]\n\n```\nregex like [^b] living in code\n```\n\n[^a]: def a\n"
    assert find_orphans(text) == []


def test_hyphenated_labels_clean():
    text = "A claim.[^north-cost]\n\n[^north-cost]: source 110\n"
    assert find_orphans(text) == []
