"""Anthropic skill-description compliance tests."""
import re
from pathlib import Path

import yaml

SKILL_MD = Path(__file__).resolve().parent.parent / "SKILL.md"


def _frontmatter():
    text = SKILL_MD.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "SKILL.md missing frontmatter"
    return yaml.safe_load(m.group(1))


def test_skill_md_has_required_fields():
    meta = _frontmatter()
    assert meta["name"] == "review-conductor"
    assert meta["license"] == "MIT"
    assert "description" in meta
    assert meta["metadata"]["workspace-aware"] is True


def test_description_contains_positive_triggers():
    meta = _frontmatter()
    desc = meta["description"].lower()
    for phrase in ["run the panel", "review chapter", "review-conductor"]:
        assert phrase in desc, f"missing positive trigger: {phrase}"


def test_description_contains_negative_triggers():
    meta = _frontmatter()
    desc = meta["description"].lower()
    assert "do not use" in desc
    for skill in ["book-knowledge", "russellian-style", "book-compose", "book-review"]:
        assert skill in desc, f"missing negative-trigger reference: {skill}"
