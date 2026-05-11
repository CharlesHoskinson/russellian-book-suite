import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _load_skill_md() -> str:
    return (ROOT / "SKILL.md").read_text(encoding="utf-8")


def _description() -> str:
    text = _load_skill_md()
    match = re.search(r"^description:\s*(.+)$", text, flags=re.MULTILINE)
    assert match, "description missing"
    return match.group(1)


def test_description_under_1024_chars():
    assert len(_description()) <= 1024


def test_description_no_xml_brackets():
    assert "<" not in _description() and ">" not in _description()


def test_positive_triggers_referenced_in_description():
    description = _description().lower()
    fixture = yaml.safe_load((ROOT / "tests/trigger_tests.yaml").read_text(encoding="utf-8"))
    matched = 0
    keywords = ("ingest", "wiki", "claim", "audit", "graph", "contradiction", "validate", "stale", "refresh", "source")
    for prompt in fixture["should_trigger"]:
        if any(k in prompt.lower() and k in description for k in keywords):
            matched += 1
    assert matched >= len(fixture["should_trigger"]) * 0.6


def test_negative_triggers_documented_in_description():
    description = _description().lower()
    refusal_terms = ["chapter drafting", "russell", "rewrite", "casual", "book-compose"]
    matched = [t for t in refusal_terms if t in description]
    assert len(matched) >= 3
