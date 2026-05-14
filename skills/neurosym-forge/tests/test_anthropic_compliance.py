# skills/neurosym-forge/tests/test_anthropic_compliance.py
"""Compliance checks for SKILL.md (Anthropic skill format)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml


SKILL_MD = Path(__file__).resolve().parent.parent / "SKILL.md"


def _frontmatter() -> dict:
    text = SKILL_MD.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "SKILL.md missing YAML frontmatter"
    return yaml.safe_load(m.group(1))


def test_skill_md_exists() -> None:
    assert SKILL_MD.exists()


def test_frontmatter_required_fields() -> None:
    fm = _frontmatter()
    for k in ("name", "description", "license"):
        assert k in fm, f"frontmatter missing {k}"


def test_name_matches_directory() -> None:
    assert _frontmatter()["name"] == "neurosym-forge"


def test_description_under_1024_chars() -> None:
    assert len(_frontmatter()["description"]) <= 1024


def test_description_has_trigger_phrases() -> None:
    desc = _frontmatter()["description"]
    for phrase in ("scaffold", "rewrite rule", "Z3"):
        assert phrase in desc, f"description missing trigger phrase {phrase!r}"


def test_body_under_500_lines() -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    body = text.split("---\n", 2)[2] if text.count("---\n") >= 2 else text
    lines = body.splitlines()
    assert len(lines) <= 500, f"SKILL.md body has {len(lines)} lines (max 500)"
