"""Tests for ci/check_windows_canary.py (windows-canary zero-marking guard)."""
from __future__ import annotations

import textwrap

from ci.check_windows_canary import full_pytest_matrix_skills, skills_missing_canary

WORKFLOW_FIXTURE = textwrap.dedent(
    """\
    jobs:
      python-skill-matrix:
        strategy:
          matrix:
            os: [ubuntu-24.04, macos-15, windows-2022]
            skill:
              - alpha
              - beta
              - gamma
            include:
              - skill: alpha
                constraints: skills/alpha/constraints.txt
              - skill: delta
                os: ubuntu-24.04
                extra: none
                smoke: import
              - skill: epsilon
                os: ubuntu-24.04
                smoke: import
    """
)


def test_parses_skill_axis_and_excludes_smoke_rows():
    skills = full_pytest_matrix_skills(WORKFLOW_FIXTURE)
    # axis skills run full pytest on Windows; smoke-only include rows do not
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


def test_real_workflow_parses_and_repo_is_clean():
    # The guard must hold on the actual repo: parse the real ci.yml and
    # confirm every full-pytest matrix skill has at least one marked test.
    from ci.check_windows_canary import REPO_ROOT, WORKFLOW_PATH

    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    skills = full_pytest_matrix_skills(text)
    assert "neurosym-forge" in skills and "paragraph-weaver" in skills
    assert "syntopical-metabook" not in skills  # smoke-only row
    assert skills_missing_canary(skills, REPO_ROOT / "skills") == []
