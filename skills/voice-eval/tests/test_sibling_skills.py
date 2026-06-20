# skills/voice-eval/tests/test_sibling_skills.py
"""Cites REQ-VEVAL-011 (signal scoring via sibling) — repo-first resolution."""
import pytest

pytestmark = pytest.mark.windows_canary


def test_resolves_repo_sibling_root(tmp_path, monkeypatch):
    from scripts.sibling_skills import sibling_root, SiblingNotFoundError
    # russellian-style is a repo sibling of voice-eval; resolve must find it.
    root = sibling_root("russellian-style")
    assert (root / "SKILL.md").is_file()


def test_missing_sibling_raises():
    from scripts.sibling_skills import sibling_root, SiblingNotFoundError
    with pytest.raises(SiblingNotFoundError):
        sibling_root("no-such-skill")
