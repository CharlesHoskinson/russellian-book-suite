import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _frontmatter() -> dict:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, flags=re.DOTALL)
    assert match, "SKILL.md missing frontmatter"
    return yaml.safe_load(match.group(1))


def test_skill_md_exists_with_exact_case():
    candidates = [p.name for p in ROOT.iterdir() if p.is_file()]
    assert "SKILL.md" in candidates


def test_no_readme_in_skill_folder():
    forbidden = [p for p in ROOT.iterdir() if p.is_file() and p.name.lower() == "readme.md"]
    assert forbidden == [], "README.md is forbidden inside a skill folder"


def test_name_is_kebab_case_no_reserved():
    fm = _frontmatter()
    name = fm["name"]
    assert re.fullmatch(r"[a-z][a-z0-9-]*", name), f"name not kebab-case: {name}"
    assert "claude" not in name and "anthropic" not in name
    assert len(name) <= 64


def test_description_meets_anthropic_constraints():
    fm = _frontmatter()
    desc = fm["description"]
    assert len(desc) <= 1024
    assert "<" not in desc and ">" not in desc
    assert "use when" in desc.lower()
    assert "do not" in desc.lower() or "do NOT" in desc


def test_progressive_disclosure_directories_exist():
    for sub in ("references", "scripts", "assets", "tests"):
        assert (ROOT / sub).is_dir(), f"missing {sub}/"


def test_skill_md_under_size_limit():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert len(text.splitlines()) <= 400
