"""Lock the non-vacuous SHACL-violation baseline before the SHACL->EDN port.

These assertions prove the violating-workspace fixture fires three *specific*
constraints (confidence range, verified-without-source, chapter-section citing a
non-verified claim) rather than ">=3 of anything", so a later port that silently
drops a constraint cannot pass by coincidence.
"""
from __future__ import annotations

import pytest

from rdflib import Dataset

pytestmark = pytest.mark.windows_canary

from scripts.validate_shacl import validate_shacl

from tests.fixtures.violating_workspace import build_violating_workspace


def test_violating_workspace_emits_triples(tmp_path, monkeypatch):
    monkeypatch.delenv("KG_BACKEND", raising=False)
    layout = build_violating_workspace(tmp_path)
    trig = layout.dataset.read_text(encoding="utf-8")
    assert trig.strip(), "projected dataset must not be empty"
    # Structural check: parse the dataset and assert a non-trivial quad count plus
    # the presence of all three injected node URIs (not a mere dot count).
    ds = Dataset()
    ds.parse(layout.dataset, format="trig")
    assert sum(1 for _ in ds.quads()) > 5, "expected a non-trivial dataset"
    for marker in ("inj-bad-confidence", "inj-verified-no-source", "inj-section"):
        assert marker in trig, f"missing injected node {marker} in TriG"


def test_violating_workspace_does_not_conform(tmp_path, monkeypatch):
    monkeypatch.delenv("KG_BACKEND", raising=False)
    layout = build_violating_workspace(tmp_path)
    report = validate_shacl(layout)
    assert report.conforms is False
    # Exactly 4 reportable violations, one per injected defect:
    #   1. confidence-range (tbf:ClaimShape) on inj-bad-confidence
    #   2. tbf:hasSourceSpan minCount on inj-verified-no-source
    #   3. "Verified claims must derive..." sh:sparql on inj-verified-no-source
    #   4. ChapterSection sh:sparql on inj-section
    assert len(report.violations) == 4, (
        "expected exactly 4 violations; got "
        f"{[(v.focus_node, v.path, v.message) for v in report.violations]}"
    )


def test_confidence_range_violation_present(tmp_path, monkeypatch):
    """(a) A claim with confidence outside 0.0-1.0 fires the range constraint."""
    monkeypatch.delenv("KG_BACKEND", raising=False)
    layout = build_violating_workspace(tmp_path)
    report = validate_shacl(layout)
    assert any(
        "confidence" in v.path for v in report.violations
    ), f"expected a tbf:confidence path violation; got {[v.path for v in report.violations]}"
    assert any(
        "confidence" in v.path and "inj-bad-confidence" in v.focus_node
        for v in report.violations
    ), (
        "expected the confidence violation on inj-bad-confidence; got "
        f"{[v.focus_node for v in report.violations]}"
    )


def test_verified_without_source_violation_present(tmp_path, monkeypatch):
    """(b) A verified claim with no source-span fires BOTH the minCount and sparql."""
    monkeypatch.delenv("KG_BACKEND", raising=False)
    layout = build_violating_workspace(tmp_path)
    report = validate_shacl(layout)
    assert any(
        "hasSourceSpan" in v.path for v in report.violations
    ), f"expected a tbf:hasSourceSpan minCount violation; got {[v.path for v in report.violations]}"
    assert any(
        "hasSourceSpan" in v.path and "inj-verified-no-source" in v.focus_node
        for v in report.violations
    ), (
        "expected the hasSourceSpan violation on inj-verified-no-source; got "
        f"{[v.focus_node for v in report.violations]}"
    )
    assert any(
        "Verified claims must derive" in v.message for v in report.violations
    ), "expected the verified-claims-must-derive sparql message"
    assert any(
        "Verified claims must derive" in v.message
        and "inj-verified-no-source" in v.focus_node
        for v in report.violations
    ), (
        "expected the verified-derives violation on inj-verified-no-source; got "
        f"{[v.focus_node for v in report.violations]}"
    )


def test_chapter_section_violation_present(tmp_path, monkeypatch):
    """(c) A chapter section citing a non-verified claim fires ChapterSectionShape."""
    monkeypatch.delenv("KG_BACKEND", raising=False)
    layout = build_violating_workspace(tmp_path)
    report = validate_shacl(layout)
    assert any(
        "Chapter sections must only cite verified claims" in v.message
        for v in report.violations
    ), "expected the chapter-section sparql message"
    assert any(
        "Chapter sections must only cite verified claims" in v.message
        and "inj-section" in v.focus_node
        for v in report.violations
    ), (
        "expected the chapter-section violation on inj-section; got "
        f"{[v.focus_node for v in report.violations]}"
    )


def test_fixture_is_deterministic_across_tmp_paths(tmp_path, monkeypatch):
    """Calling the helper twice yields equivalent violation sets (sans tmp path)."""
    monkeypatch.delenv("KG_BACKEND", raising=False)
    layout_a = build_violating_workspace(tmp_path / "a")
    layout_b = build_violating_workspace(tmp_path / "b")
    msgs_a = sorted(v.message for v in validate_shacl(layout_a).violations)
    msgs_b = sorted(v.message for v in validate_shacl(layout_b).violations)
    assert msgs_a == msgs_b
