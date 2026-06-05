"""Tests for ci/compute_matrix.py (REQ-CI-046 dynamic matrix selection)."""
from __future__ import annotations

from ci.compute_matrix import (
    build_rows,
    runnable,
    select_skills,
    shared_hit,
)

CONFIG = {
    "shared_paths": [
        ".github/workflows/ci.yml",
        ".github/actions/**",
        ".github/ci/skills-matrix.json",
        "ci/**",
    ],
    "defaults": {"os": ["ubuntu-24.04", "macos-15", "windows-2022"], "extra": "ci", "timeout": 15},
    "skills": [
        {"skill": "alpha"},
        {"skill": "beta", "constraints": "skills/beta/constraints.txt"},
        {
            "skill": "gamma",
            "extra": "dev,semantic",
            "hf_model": "org/model-x",
            "pytest_workers": "auto",
            "timeout": 20,
        },
        {"skill": "delta", "os": ["ubuntu-24.04"], "extra": "none", "smoke": "import"},
        {
            "skill": "epsilon",
            "siblings": ["alpha", "beta"],
            "spacy": True,
            "pytest_deselect": "--deselect tests/test_s.py::test_v",
        },
        {"skill": "zeta", "ci": "none", "reason": "templates only"},
    ],
}


def test_runnable_excludes_ci_none():
    names = [e["skill"] for e in runnable(CONFIG)]
    assert names == ["alpha", "beta", "gamma", "delta", "epsilon"]


def test_shared_hit_exact_and_glob():
    assert shared_hit([".github/workflows/ci.yml"], CONFIG["shared_paths"])
    assert shared_hit([".github/actions/setup-models/action.yml"], CONFIG["shared_paths"])
    assert shared_hit(["ci/compute_matrix.py"], CONFIG["shared_paths"])
    assert not shared_hit(["skills/alpha/scripts/x.py", "docs/y.md"], CONFIG["shared_paths"])


def test_pr_selects_only_touched_skills():
    sel = select_skills(CONFIG, "pull_request", ["skills/alpha/tests/test_a.py", "docs/z.md"])
    assert [e["skill"] for e in sel] == ["alpha"]


def test_pr_with_shared_path_selects_all():
    sel = select_skills(CONFIG, "pull_request", ["ci/compute_matrix.py"])
    assert len(sel) == 5


def test_push_selects_all_regardless_of_paths():
    sel = select_skills(CONFIG, "push", [])
    assert len(sel) == 5


def test_merge_group_selects_all():
    assert len(select_skills(CONFIG, "merge_group", [])) == 5


def test_docs_only_pr_selects_nothing():
    assert select_skills(CONFIG, "pull_request", ["docs/z.md", "README.md"]) == []


def test_build_rows_pr_profile_expands_os_and_defaults():
    rows = build_rows(runnable(CONFIG), CONFIG, profile="pr")
    # alpha/beta/gamma/epsilon x 3 OS + delta x 1 OS = 13
    assert len(rows) == 13
    alpha_rows = [r for r in rows if r["skill"] == "alpha"]
    assert {r["os"] for r in alpha_rows} == {"ubuntu-24.04", "macos-15", "windows-2022"}
    r = alpha_rows[0]
    # every row carries every key (GitHub include rows must be uniform)
    assert r["extra"] == "ci" and r["timeout"] == 15 and r["spacy"] == "false"
    assert r["hf_model"] == "" and r["siblings"] == "" and r["smoke"] == ""
    assert r["constraints"] == "" and r["pytest_deselect"] == "" and r["pytest_workers"] == ""
    assert r["python_version"] == "3.13"


def test_build_rows_overrides_flow_through():
    rows = build_rows(runnable(CONFIG), CONFIG, profile="pr")
    gamma = next(r for r in rows if r["skill"] == "gamma" and r["os"] == "windows-2022")
    assert gamma["hf_model"] == "org/model-x" and gamma["timeout"] == 20
    assert gamma["pytest_workers"] == "auto" and gamma["extra"] == "dev,semantic"
    eps = next(r for r in rows if r["skill"] == "epsilon")
    assert eps["siblings"] == "alpha beta" and eps["spacy"] == "true"
    delta = [r for r in rows if r["skill"] == "delta"]
    assert len(delta) == 1 and delta[0]["os"] == "ubuntu-24.04" and delta[0]["smoke"] == "import"
    beta = next(r for r in rows if r["skill"] == "beta")
    assert beta["constraints"] == "skills/beta/constraints.txt"


def test_windows_canary_profile_one_windows_row_per_skill():
    rows = build_rows(runnable(CONFIG), CONFIG, profile="windows-canary")
    assert len(rows) == 5
    assert all(r["os"] == "windows-2022" for r in rows)
    # smoke rows ride along (install+import on Windows is the nightly's job)
    assert any(r["skill"] == "delta" and r["smoke"] == "import" for r in rows)


def test_python_compat_profile_linux_times_versions_drops_constraints():
    rows = build_rows(
        runnable(CONFIG), CONFIG, profile="python-compat", python_versions=["3.11", "3.12"]
    )
    assert len(rows) == 10  # 5 skills x 2 versions
    assert all(r["os"] == "ubuntu-24.04" for r in rows)
    assert {r["python_version"] for r in rows} == {"3.11", "3.12"}
    beta = next(r for r in rows if r["skill"] == "beta")
    assert beta["constraints"] == ""  # 3.13-generated pins must not leak to 3.11/3.12
