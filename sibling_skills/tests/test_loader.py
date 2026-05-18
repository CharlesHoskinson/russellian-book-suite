import pytest
from sibling_skills import load_skill_api, IncompatibleSkillApiVersion

def test_load_skill_api_returns_module(tmp_path, monkeypatch):
    skill = tmp_path / "demo-skill"
    skill.mkdir()
    (skill / "skill_api.py").write_text(
        "API_VERSION = (0, 1)\n"
        "__all__ = ['hello']\n"
        "def hello(name: str) -> str:\n"
        "    return f'hi {name}'\n"
    )
    monkeypatch.setenv("SIBLING_SKILLS_ROOT", str(tmp_path))
    mod = load_skill_api("demo-skill")
    assert mod.hello("x") == "hi x"
    assert mod.API_VERSION == (0, 1)

def test_load_skill_api_raises_on_major_mismatch(tmp_path, monkeypatch):
    skill = tmp_path / "demo-skill"
    skill.mkdir()
    (skill / "skill_api.py").write_text("API_VERSION = (2, 0)\n__all__ = []\n")
    monkeypatch.setenv("SIBLING_SKILLS_ROOT", str(tmp_path))
    with pytest.raises(IncompatibleSkillApiVersion) as exc:
        load_skill_api("demo-skill", expected_major=1)
    assert "(2, 0)" in str(exc.value)
    assert "expected major 1" in str(exc.value)

def test_load_skill_api_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("SIBLING_SKILLS_ROOT", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        load_skill_api("nonexistent-skill")
