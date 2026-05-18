from pathlib import Path

def test_skill_api_loads_via_sibling_skills(monkeypatch):
    skills_root = Path(__file__).resolve().parents[3]  # .../russellian-book-suite/skills
    monkeypatch.setenv("SIBLING_SKILLS_ROOT", str(skills_root))
    from sibling_skills import load_skill_api
    mod = load_skill_api("scrapling-fetch", expected_major=0)
    assert callable(mod.fetch)
    assert mod.API_VERSION == (0, 1)
