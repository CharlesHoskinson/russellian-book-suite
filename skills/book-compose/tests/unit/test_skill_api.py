"""Unit tests for the book-compose public skill_api surface (IF-BC-1)."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

from datetime import datetime
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from skill_api import (
    read_lens,
    Lens,
    LensContractViolation,
    API_VERSION,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_FRONTMATTER = """\
---
chapter_id: ch-03
generated_at: "2026-05-17T10:00:00Z"
source_run_id: run-abc123
n_topics: 4
n_disputed: 2
n_concepts: 6
coverage_score: 0.82
---
"""

VALID_SECTIONS = """\
## Topics

Some topics content.

## Disputed Questions

Some disputed content.

## Concept Reconciliation

Some concept content.

## Coverage

Some coverage content.
"""

VALID_LENS = VALID_FRONTMATTER + VALID_SECTIONS


def _make_workspace(tmp_path: Path, chapter_id: str, content: str) -> Path:
    ws = tmp_path / "book"
    ws.mkdir()
    lens_dir = ws / "syntopical" / "lenses"
    lens_dir.mkdir(parents=True)
    (lens_dir / f"{chapter_id}.md").write_text(content, encoding="utf-8")
    return ws


# ---------------------------------------------------------------------------
# IF-BC-0: API surface
# ---------------------------------------------------------------------------

def test_api_version():
    assert API_VERSION == (0, 1)


# ---------------------------------------------------------------------------
# IF-BC-1: read_lens
# ---------------------------------------------------------------------------

def test_read_lens_returns_lens(tmp_path):
    ws = _make_workspace(tmp_path, "ch-03", VALID_LENS)
    lens = read_lens("ch-03", ws)
    assert isinstance(lens, Lens)


def test_read_lens_chapter_id(tmp_path):
    ws = _make_workspace(tmp_path, "ch-03", VALID_LENS)
    lens = read_lens("ch-03", ws)
    assert lens.chapter_id == "ch-03"


def test_read_lens_frontmatter_fields(tmp_path):
    ws = _make_workspace(tmp_path, "ch-03", VALID_LENS)
    lens = read_lens("ch-03", ws)
    assert isinstance(lens.generated_at, datetime)
    assert lens.source_run_id == "run-abc123"
    assert lens.n_topics == 4
    assert lens.n_disputed == 2
    assert lens.n_concepts == 6
    assert abs(lens.coverage_score - 0.82) < 1e-6


def test_read_lens_section_content(tmp_path):
    ws = _make_workspace(tmp_path, "ch-03", VALID_LENS)
    lens = read_lens("ch-03", ws)
    assert "topics" in lens.topics_md.lower() or lens.topics_md.strip() != ""
    assert lens.disputed_md.strip() != ""
    assert lens.concepts_md.strip() != ""
    assert lens.coverage_md.strip() != ""


def test_read_lens_canonical_path(tmp_path):
    ws = _make_workspace(tmp_path, "ch-07", VALID_LENS)
    # Should read from syntopical/lenses/ch-07.md
    lens = read_lens("ch-07", ws)
    assert lens.chapter_id == "ch-07"


def test_read_lens_missing_file_raises(tmp_path):
    ws = tmp_path / "book"
    ws.mkdir()
    (ws / "syntopical" / "lenses").mkdir(parents=True)
    with pytest.raises(FileNotFoundError):
        read_lens("ch-99", ws)


def test_read_lens_wrong_section_order_raises(tmp_path):
    bad_content = VALID_FRONTMATTER + """\
## Disputed Questions

Content.

## Topics

Content.

## Concept Reconciliation

Content.

## Coverage

Content.
"""
    ws = _make_workspace(tmp_path, "ch-03", bad_content)
    with pytest.raises(LensContractViolation):
        read_lens("ch-03", ws)


def test_read_lens_missing_section_raises(tmp_path):
    bad_content = VALID_FRONTMATTER + """\
## Topics

Content.

## Disputed Questions

Content.
"""
    ws = _make_workspace(tmp_path, "ch-03", bad_content)
    with pytest.raises(LensContractViolation):
        read_lens("ch-03", ws)
