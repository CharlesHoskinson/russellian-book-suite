"""Fixture-based tests for `book-qa.lint_artifact` covering defect classes D1-D8.

Each test stages a tiny workspace into ``tmp_path`` with a chosen fixture
markdown (and optional HTML / asset files), runs ``lint_artifact`` end-to-end,
and asserts that the *dirty* fixture surfaces at least one defect of the
target class while the *clean* counterpart surfaces none of that class.

The clean fixtures may still emit *other* defect classes (e.g. a short D1
clean fixture under-runs the D5 word-count band). The smoke test at the end
of the file exercises a fully-clean manuscript designed to satisfy every
band simultaneously and expects zero defects in total.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.lint_artifact import lint_artifact


def _classes(defects) -> set[str]:
    return {d.class_ for d in defects}


# --------------------------------------------------------------------- helpers


def _run(stage_release, md: str, html: str | None = None,
         assets: list[tuple[str, str]] | None = None):
    workspace, version = stage_release(md, html, assets)
    defects, summary = lint_artifact(workspace, version)
    return defects, summary


# --------------------------------------------------------------------- D1


def test_d1_orphan_tokens_dirty(stage_release):
    defects, _ = _run(stage_release, "d1_dirty.md")
    assert "D1" in _classes(defects), \
        f"expected D1 in dirty fixture; got {sorted(_classes(defects))}"


def test_d1_orphan_tokens_clean(stage_release):
    defects, _ = _run(stage_release, "d1_clean.md")
    assert "D1" not in _classes(defects), \
        f"unexpected D1 in clean fixture: {[d for d in defects if d.class_ == 'D1']}"


# --------------------------------------------------------------------- D2


def test_d2_raw_md_bleed_dirty(stage_release):
    defects, _ = _run(stage_release, "d2_dirty.md")
    assert "D2" in _classes(defects)


def test_d2_raw_md_bleed_clean(stage_release):
    defects, _ = _run(stage_release, "d2_clean.md")
    assert "D2" not in _classes(defects)


# --------------------------------------------------------------------- D3


def test_d3_broken_xref_dirty(stage_release):
    defects, _ = _run(stage_release, "d3_dirty.md")
    assert "D3" in _classes(defects)


def test_d3_broken_xref_clean(stage_release):
    # Clean fixture references figures/placeholder.png; stage that asset too.
    defects, _ = _run(
        stage_release,
        "d3_clean.md",
        assets=[("placeholder.png", "figures/placeholder.png")],
    )
    assert "D3" not in _classes(defects), \
        f"unexpected D3 in clean fixture: {[d for d in defects if d.class_ == 'D3']}"


# --------------------------------------------------------------------- D4


def test_d4_hierarchy_dirty(stage_release):
    defects, _ = _run(stage_release, "d4_dirty.md")
    assert "D4" in _classes(defects)


def test_d4_hierarchy_clean(stage_release):
    defects, _ = _run(stage_release, "d4_clean.md")
    assert "D4" not in _classes(defects)


# --------------------------------------------------------------------- D5


def test_d5_count_contracts_dirty(stage_release):
    defects, _ = _run(stage_release, "d5_dirty.md")
    assert "D5" in _classes(defects), \
        "500-word chapter must trip the D5 word-count band"


def test_d5_count_contracts_clean(stage_release):
    defects, _ = _run(stage_release, "d5_clean.md")
    assert "D5" not in _classes(defects), \
        f"clean D5 fixture should land in all bands; got {[d for d in defects if d.class_ == 'D5']}"


# --------------------------------------------------------------------- D6


def test_d6_paragraph_variance_dirty(stage_release):
    defects, _ = _run(stage_release, "d6_dirty.md")
    assert "D6" in _classes(defects), \
        "uniform paragraphs must trip the D6 coefficient-of-variation check"


def test_d6_paragraph_variance_clean(stage_release):
    defects, _ = _run(stage_release, "d6_clean.md")
    assert "D6" not in _classes(defects)


# --------------------------------------------------------------------- D7


def test_d7_css_reset_dirty(stage_release):
    defects, _ = _run(stage_release, "d7_md_stub.md", "d7_dirty.html")
    assert "D7" in _classes(defects), \
        "Tailwind preflight without a heading override must trip D7"


def test_d7_css_reset_clean(stage_release):
    defects, _ = _run(stage_release, "d7_md_stub.md", "d7_clean.html")
    assert "D7" not in _classes(defects)


# --------------------------------------------------------------------- D8


def test_d8_asset_404_dirty(stage_release):
    defects, _ = _run(stage_release, "d8_dirty.md")
    assert "D8" in _classes(defects)


def test_d8_asset_404_clean(stage_release):
    defects, _ = _run(
        stage_release,
        "d8_clean.md",
        assets=[("placeholder.png", "figures/placeholder.png")],
    )
    assert "D8" not in _classes(defects), \
        f"unexpected D8 in clean fixture: {[d for d in defects if d.class_ == 'D8']}"


# --------------------------------------------------------------------- smoke


def test_smoke_clean_manuscript_has_zero_defects(stage_release):
    """End-to-end run against a fully-clean fixture. Expects ``lint_artifact``
    to return zero defects across all eight classes."""
    defects, summary = _run(
        stage_release,
        "smoke_clean.md",
        "smoke_clean.html",
    )
    assert summary["total_defects"] == 0, (
        f"clean manuscript produced defects: "
        f"{[(d.class_, d.detail) for d in defects]}"
    )


# --------------------------------------------------------------------- parametric sanity


@pytest.mark.parametrize(
    "dirty_md,expected_class",
    [
        ("d1_dirty.md", "D1"),
        ("d2_dirty.md", "D2"),
        ("d3_dirty.md", "D3"),
        ("d4_dirty.md", "D4"),
        ("d5_dirty.md", "D5"),
        ("d6_dirty.md", "D6"),
        ("d8_dirty.md", "D8"),
    ],
)
def test_dirty_fixtures_emit_expected_class(stage_release, dirty_md, expected_class):
    """Parametric sweep that every dirty markdown fixture surfaces its
    nominal defect class. D7 is excluded because it requires an HTML pair."""
    defects, _ = _run(stage_release, dirty_md)
    assert expected_class in _classes(defects), (
        f"{dirty_md!r} did not surface {expected_class}; "
        f"classes seen: {sorted(_classes(defects))}"
    )
