"""Tests for lint_supports.py."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compile_thesis import compile_thesis  # noqa: E402
from lint_supports import lint, scan_paragraphs  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
THESIS_YAML = FIXTURES / "tiny-thesis.yaml"


def _prepare(tmp_path: Path, manuscript_name: str, extra_ttl: str = "") -> Path:
    """Lay out a workspace with the compiled tiny-thesis TTL and a manuscript.

    Returns the workspace path. ``extra_ttl`` is appended to the compiled
    ``thesis-triples.ttl`` so individual tests can inject orphan nodes.
    """
    (tmp_path / "thesis").mkdir()
    shutil.copy(THESIS_YAML, tmp_path / "thesis" / "tiny.yaml")
    compile_thesis(tmp_path, "tiny")
    if extra_ttl:
        ttl_path = tmp_path / ".knowledge" / "thesis-triples.ttl"
        with ttl_path.open("a", encoding="utf-8") as fh:
            fh.write("\n" + extra_ttl + "\n")

    release_dir = tmp_path / "book" / "releases" / "v1"
    release_dir.mkdir(parents=True)
    shutil.copy(FIXTURES / manuscript_name, release_dir / "manuscript.md")
    return tmp_path


def test_scan_paragraphs_skips_footnote_definitions() -> None:
    md = (
        "# Chapter 1\n\n"
        "<!-- supports: thesis -->\n"
        "A genuine paragraph with enough words to count as prose.\n\n"
        "[^a]: A footnote definition that must not be scanned as a paragraph.\n"
    )
    raws = [p.raw for p in scan_paragraphs(md)]
    assert any("genuine paragraph" in r for r in raws)
    assert not any(r.lstrip().startswith("[^a]") for r in raws)


def test_finds_orphan_no_support(tmp_path: Path) -> None:
    workspace = _prepare(tmp_path, "manuscript-no-support.md")
    defects, summary = lint(workspace, "v1")
    kinds = [d.kind for d in defects if d.class_ == "D9"]
    assert "no-support" in kinds
    assert summary["orphan_no_support"] >= 1
    assert summary["orphan_broken_supports"] == 0


def test_finds_broken_supports(tmp_path: Path) -> None:
    workspace = _prepare(tmp_path, "manuscript-broken.md")
    defects, summary = lint(workspace, "v1")
    broken = [d for d in defects if d.kind == "broken-supports"]
    assert len(broken) == 1
    assert "ghost-node" in broken[0].detail
    assert summary["orphan_broken_supports"] == 1


def test_finds_unreachable(tmp_path: Path) -> None:
    # Inject a SubArgument node that has no :supports edge — orphaned in the tree.
    extra = (
        '@prefix : <https://russellian.book/thesis/> .\n'
        '@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n'
        ':lonely-node rdf:type :SubArgument ;\n'
        '    :statement "An orphan node that reaches nothing." .\n'
    )
    workspace = _prepare(tmp_path, "manuscript-unreachable.md", extra_ttl=extra)
    defects, summary = lint(workspace, "v1")
    unreach = [d for d in defects if d.kind == "unreachable"]
    assert len(unreach) == 1
    assert "lonely-node" in unreach[0].detail
    assert summary["orphan_unreachable"] == 1


def test_clean_paragraph_passes(tmp_path: Path) -> None:
    workspace = _prepare(tmp_path, "manuscript-clean.md")
    defects, summary = lint(workspace, "v1")
    d9_defects = [d for d in defects if d.class_ == "D9"]
    assert d9_defects == []
    assert summary["orphan_no_support"] == 0
    assert summary["orphan_broken_supports"] == 0
    assert summary["orphan_unreachable"] == 0
    assert summary["supported"] == 2


def test_untracked_manuscript_is_not_flagged_orphan(tmp_path: Path) -> None:
    """3.7: a manuscript that declares NO supports carriers (e.g. a freshly
    assembled one) is treated as not-in-supports-tracking-mode — it is not
    flooded with D9 no-support orphans, nor D12 unadvanced sub-arguments."""
    workspace = _prepare(tmp_path, "manuscript-untracked.md")
    defects, summary = lint(workspace, "v1")
    assert [d for d in defects if d.kind == "no-support"] == []
    assert summary["orphan_no_support"] == 0
    assert summary["unadvanced_sub_arguments"] == []
    assert summary.get("supports_tracking") is False


def test_partially_tracked_manuscript_still_flags_missing(tmp_path: Path) -> None:
    """Opt-in is per-manuscript: once ANY paragraph declares a carrier, the
    carrier-less ones are still flagged (the existing no-support fixture)."""
    workspace = _prepare(tmp_path, "manuscript-no-support.md")
    defects, summary = lint(workspace, "v1")
    assert summary.get("supports_tracking") is True
    assert summary["orphan_no_support"] >= 1
