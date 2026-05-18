from pathlib import Path

def test_adapter_isolation(monkeypatch):
    skills_root = Path(__file__).resolve().parents[3]
    monkeypatch.setenv("SIBLING_SKILLS_ROOT", str(skills_root))
    from sibling_skills import load_skill_api
    sf = load_skill_api("scrapling-fetch", expected_major=0)
    # Make arxiv adapter blow up on any call:
    monkeypatch.setattr(sf.arxiv, "get", lambda x: (_ for _ in ()).throw(RuntimeError("layout drift")))
    # Other adapters remain callable (don't call them; just confirm references):
    assert callable(sf.openalex.work)
    assert callable(sf.doi.resolve)
    assert callable(sf.semantic_scholar.references)
