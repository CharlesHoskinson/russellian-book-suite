# tests/test_skill_doc.py
from __future__ import annotations

import pytest
pytestmark = pytest.mark.windows_canary

from pathlib import Path

DOC = Path(__file__).resolve().parents[1] / "SKILL.md"


def test_skill_doc_exists():
    assert DOC.is_file()


def test_skill_doc_covers_required_sections():
    text = DOC.read_text(encoding="utf-8")
    for needed in (
        "PLAN", "BIND", "FEASIBILITY", "ORDER", "WEAVE", "REVISE",
        "provenance", "argument", "emotion", "narrative",
        "russellian-style", "book-thesis", "book-review",
    ):
        assert needed in text, f"SKILL.md missing: {needed}"


def test_skill_doc_has_frontmatter_name():
    text = DOC.read_text(encoding="utf-8")
    assert text.lstrip().startswith("---")
    assert "name: paragraph-weaver" in text
