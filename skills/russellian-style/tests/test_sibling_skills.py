"""sibling_skills loads humanizer's pattern catalog under an alias namespace."""
import pytest


def test_humanizer_available_returns_bool():
    from scripts.sibling_skills import humanizer_available
    assert isinstance(humanizer_available(), bool)


def test_load_humanizer_catalog_returns_dict_when_present():
    from scripts.sibling_skills import humanizer_available, load_humanizer_catalog
    if not humanizer_available():
        pytest.skip("humanizer not installed at ~/.claude/skills/humanizer/")
    catalog = load_humanizer_catalog()
    assert isinstance(catalog, dict)
    assert len(catalog) >= 1
    assert any(isinstance(v, (list, dict)) for v in catalog.values())


def test_load_humanizer_catalog_raises_when_absent(monkeypatch, tmp_path):
    from scripts.sibling_skills import load_humanizer_catalog, SiblingNotFoundError
    monkeypatch.setattr("scripts.sibling_skills._skills_root", lambda: tmp_path)
    with pytest.raises(SiblingNotFoundError):
        load_humanizer_catalog()
