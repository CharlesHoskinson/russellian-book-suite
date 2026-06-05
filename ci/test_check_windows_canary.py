"""Tests for ci/check_windows_canary.py (windows-canary zero-marking guard)."""
from __future__ import annotations

from ci.check_windows_canary import full_pytest_matrix_skills, skills_missing_canary

CONFIG = {
    "defaults": {"os": ["ubuntu-24.04", "macos-15", "windows-2022"]},
    "skills": [
        {"skill": "alpha"},
        {"skill": "beta"},
        {"skill": "gamma", "extra": "dev"},
        {"skill": "delta", "os": ["ubuntu-24.04"], "smoke": "import"},
        {"skill": "epsilon", "os": ["ubuntu-24.04"]},
        {"skill": "zeta", "ci": "none", "reason": "templates only"},
    ],
}


def test_selects_windows_full_pytest_entries_only():
    skills = full_pytest_matrix_skills(CONFIG)
    # smoke rows, linux-only rows, and ci:none entries never run pytest on Windows
    assert skills == {"alpha", "beta", "gamma"}


def test_missing_canary_detection(tmp_path):
    skills_dir = tmp_path / "skills"
    # alpha: marked test -> ok
    a = skills_dir / "alpha" / "tests"
    a.mkdir(parents=True)
    (a / "test_x.py").write_text(
        "import pytest\npytestmark = pytest.mark.windows_canary\n", encoding="utf-8"
    )
    # beta: tests exist but none marked -> flagged
    b = skills_dir / "beta" / "tests"
    b.mkdir(parents=True)
    (b / "test_y.py").write_text("def test_y():\n    assert True\n", encoding="utf-8")
    # gamma: decorator-style marker in a subdir -> ok
    g = skills_dir / "gamma" / "tests" / "unit"
    g.mkdir(parents=True)
    (g / "test_z.py").write_text(
        "import pytest\n@pytest.mark.windows_canary\ndef test_z():\n    assert True\n",
        encoding="utf-8",
    )
    missing = skills_missing_canary({"alpha", "beta", "gamma"}, skills_dir)
    assert missing == ["beta"]


def test_real_registry_parses_and_repo_is_clean():
    import json

    from ci.check_windows_canary import MATRIX_PATH, REPO_ROOT

    config = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    skills = full_pytest_matrix_skills(config)
    assert "neurosym-forge" in skills and "paragraph-weaver" in skills
    assert "syntopical-metabook" not in skills  # smoke-only entry
    assert skills_missing_canary(skills, REPO_ROOT / "skills") == []
