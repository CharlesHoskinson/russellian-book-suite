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


def _fake_skill_with_scripts(root, name, version=(0, 1)):
    skill = root / name
    (skill / "scripts").mkdir(parents=True)
    (skill / "scripts" / "__init__.py").write_text("", encoding="utf-8")
    (skill / "scripts" / "thing.py").write_text("VALUE = 42\n", encoding="utf-8")
    (skill / "skill_api.py").write_text(
        "from __future__ import annotations\n"
        "from dataclasses import dataclass\n"
        "from scripts.thing import VALUE\n"
        f"API_VERSION = {version}\n"
        "@dataclass\n"
        "class Result:\n    n: int\n"
        "def at_import_value():\n    return VALUE\n"
        "def deferred_value():\n    from scripts.thing import VALUE as v\n    return v\n",
        encoding="utf-8",
    )
    return skill


def test_load_skill_api_resolves_scripts_collision(tmp_path, monkeypatch):
    """A sibling whose skill_api uses absolute `from scripts.X` (import-time and
    deferred) and a dataclass must load and call correctly."""
    monkeypatch.setenv("SIBLING_SKILLS_ROOT", str(tmp_path))
    _fake_skill_with_scripts(tmp_path, "scripted-skill")
    api = load_skill_api("scripted-skill", expected_major=0)
    assert api.at_import_value() == 42      # import-time `from scripts.thing`
    assert api.deferred_value() == 42       # call-time `from scripts.thing` via the swap
    assert api.Result(n=3).n == 3           # dataclass loaded (module registered pre-exec)


def test_load_skill_api_no_scripts_leakage(tmp_path, monkeypatch):
    import sys, types
    monkeypatch.setenv("SIBLING_SKILLS_ROOT", str(tmp_path))
    _fake_skill_with_scripts(tmp_path, "scripted-skill")
    sentinel = types.ModuleType("scripts")
    sentinel.__marker__ = "caller-owned"
    monkeypatch.setitem(sys.modules, "scripts", sentinel)
    api = load_skill_api("scripted-skill", expected_major=0)
    api.deferred_value()  # triggers a swap+restore
    assert sys.modules.get("scripts") is sentinel
