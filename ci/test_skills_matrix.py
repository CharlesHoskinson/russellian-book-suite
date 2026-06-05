"""REQ-CI-045: every skills/* directory is registered in skills-matrix.json.

A skill directory is any child of skills/ containing SKILL.md (the public
skill contract). Registration is either a runnable matrix entry or an
explicit {"ci": "none", "reason": ...} opt-out.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = REPO_ROOT / ".github" / "ci" / "skills-matrix.json"
SKILLS_DIR = REPO_ROOT / "skills"


def _config() -> dict:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def _skill_dirs() -> set[str]:
    return {
        p.name
        for p in SKILLS_DIR.iterdir()
        if p.is_dir() and (p / "SKILL.md").exists()
    }


def test_every_skill_dir_is_registered():
    registered = {e["skill"] for e in _config()["skills"]}
    missing = _skill_dirs() - registered
    assert not missing, (
        f"skills {sorted(missing)} have no entry in .github/ci/skills-matrix.json — "
        "add a runnable entry or an explicit ci:none opt-out with a reason"
    )


def test_every_entry_has_a_skill_dir():
    ghosts = {e["skill"] for e in _config()["skills"]} - {
        p.name for p in SKILLS_DIR.iterdir() if p.is_dir()
    }
    assert not ghosts, f"matrix entries {sorted(ghosts)} have no skills/ directory"


def test_no_duplicate_entries():
    names = [e["skill"] for e in _config()["skills"]]
    assert len(names) == len(set(names)), "duplicate skill entries in skills-matrix.json"


def test_ci_none_entries_carry_a_reason():
    for e in _config()["skills"]:
        if e.get("ci") == "none":
            assert e.get("reason", "").strip(), (
                f"{e['skill']}: ci:none requires a non-empty reason"
            )


def test_runnable_pytest_entries_have_a_tests_dir():
    for e in _config()["skills"]:
        if e.get("ci") == "none" or e.get("smoke"):
            continue
        tests = SKILLS_DIR / e["skill"] / "tests"
        assert tests.is_dir(), (
            f"{e['skill']} is a runnable full-pytest entry but has no tests/ dir"
        )


def test_defaults_cover_three_oses():
    """REQ-CI-040: the default OS axis is exactly the three supported labels."""
    assert _config()["defaults"]["os"] == ["ubuntu-24.04", "macos-15", "windows-2022"]
