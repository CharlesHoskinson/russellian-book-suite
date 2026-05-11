"""Fixture-based tests for `book-qa.lint_artifact` covering defect classes D1-D12.

Each test stages a tiny workspace into ``tmp_path`` with a chosen fixture
markdown (and optional HTML / asset files), runs ``lint_artifact`` end-to-end,
and asserts that the *dirty* fixture surfaces at least one defect of the
target class while the *clean* counterpart surfaces none of that class.

The clean fixtures may still emit *other* defect classes (e.g. a short D1
clean fixture under-runs the D5 word-count band). The smoke test at the end
of the file exercises a fully-clean manuscript designed to satisfy every
band simultaneously and expects zero defects in total.

D9-D12 defects come from JSON side-files emitted by the `book-thesis`
pipeline; the linter just reads them. The tests stage a minimal manuscript
and drop a small fixture JSON into `<workspace>/qa/` to verify each pickup.
"""
from __future__ import annotations

import json
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


# --------------------------------------------------------------------- D9-D12


def _write_qa_json(workspace: Path, name: str, payload: dict | list) -> None:
    qa_dir = workspace / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    (qa_dir / name).write_text(json.dumps(payload), encoding="utf-8")


def test_d9_orphan_paragraph_picked_up_from_supports_defects_json(stage_release):
    workspace, version = stage_release("smoke_clean.md", "smoke_clean.html")
    _write_qa_json(workspace, "supports-defects.json", {
        "summary": {"orphan_count": 1, "unadvanced_sub_arguments": []},
        "defects": [
            {
                "class": "D9",
                "severity": "critical",
                "where": "ch-03 paragraph 7",
                "detail": "paragraph has no supports: frontmatter and does not reach :Thesis",
                "fix_hint": "add `supports:` pointing at a thesis sub-argument node",
            },
        ],
    })
    defects, summary = lint_artifact(workspace, version)
    d9 = [d for d in defects if d.class_ == "D9"]
    assert d9, f"expected D9 in defects; got {sorted(_classes(defects))}"
    assert d9[0].severity == "critical"
    assert "ch-03" in d9[0].where
    assert summary["by_class"].get("D9") == 1


def test_d10_transitive_contradiction_picked_up_from_datalog_defects_json(stage_release):
    workspace, version = stage_release("smoke_clean.md", "smoke_clean.html")
    _write_qa_json(workspace, "datalog-defects.json", {
        "defects": [
            {
                "class": "D10",
                "severity": "critical",
                "where": "ch-02 vs ch-07",
                "detail": "transitive contradiction: A->B in ch-02 conflicts with B->!A in ch-07",
                "fix_hint": "reconcile the conflicting claims or revise the thesis tree",
            },
            # noise: non-D10 entries must be ignored
            {"class": "D99", "severity": "minor", "where": "elsewhere", "detail": "ignored"},
        ],
    })
    defects, summary = lint_artifact(workspace, version)
    d10 = [d for d in defects if d.class_ == "D10"]
    assert d10, f"expected D10 in defects; got {sorted(_classes(defects))}"
    assert d10[0].severity == "critical"
    assert summary["by_class"].get("D10") == 1


def test_d11_failed_entailment_picked_up_from_entailment_results_json(stage_release):
    workspace, version = stage_release("smoke_clean.md", "smoke_clean.html")
    _write_qa_json(workspace, "entailment-results.json", {
        "results": [
            {
                "paragraph_id": "ch-05-p12",
                "supports": "history-shapes-government",
                "verdict": "contradicts",
            },
            {
                "paragraph_id": "ch-05-p18",
                "supports": "geography-shapes-economy",
                "verdict": "unrelated",
            },
            # entailed verdicts must NOT produce defects
            {
                "paragraph_id": "ch-05-p20",
                "supports": "geography-shapes-economy",
                "verdict": "entailed",
            },
        ],
    })
    defects, summary = lint_artifact(workspace, version)
    d11 = [d for d in defects if d.class_ == "D11"]
    assert len(d11) == 2, f"expected 2 D11 defects; got {len(d11)}"
    verdicts_in_detail = " ".join(d.detail for d in d11)
    assert "contradicts" in verdicts_in_detail
    assert "unrelated" in verdicts_in_detail
    assert all(d.severity == "critical" for d in d11)
    assert summary["by_class"].get("D11") == 2


def test_d12_unadvanced_sub_argument_picked_up(stage_release):
    workspace, version = stage_release("smoke_clean.md", "smoke_clean.html")
    _write_qa_json(workspace, "supports-defects.json", {
        "summary": {
            "orphan_count": 0,
            "unadvanced_sub_arguments": [
                {"id": "geography-shapes-economy"},
                {"id": "history-shapes-government"},
            ],
        },
        "defects": [],
    })
    defects, summary = lint_artifact(workspace, version)
    d12 = [d for d in defects if d.class_ == "D12"]
    assert len(d12) == 2, f"expected 2 D12 defects; got {len(d12)}"
    assert all(d.severity == "important" for d in d12)
    nodes = " ".join(d.detail for d in d12)
    assert "geography-shapes-economy" in nodes
    assert "history-shapes-government" in nodes
    assert summary["by_class"].get("D12") == 2
    assert summary["by_severity"].get("important") == 2
