# ci-consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One source of truth for the python-skill matrix, PR-scoped matrix legs, death-spiral-proof model caches, no ci-legacy, no copy-paste between workflows.

**Architecture:** A JSON registry (`.github/ci/skills-matrix.json`) is consumed by a `compute-matrix` job (`ci/compute_matrix.py`), by the windows-canary guard, and by registration lints. Model caching moves into a `setup-models` composite with explicit restore/save. ci-legacy's unique coverage moves to the nightly.

**Tech Stack:** GitHub Actions, stdlib-only Python in `ci/`, pytest, actionlint.

**Conventions:** All `uses:` refs are SHA-pinned with a `# vX.Y.Z` comment (repo standard since P1 hardening). Reuse the SHAs already present in `ci.yml` / `nightly-flake-drift.yml` for checkout, github-script, cache, setup-python. For actions not yet pinned anywhere (`setup-node`, `setup-java`, `upload-artifact` if absent), resolve the SHA with `gh api repos/<owner>/<action>/git/ref/tags/<tag> --jq .object.sha` (dereference annotated tags with `git/tags/<sha>` if `.object.type == "tag"`).

REQ coverage: REQ-CI-040 (T2, T5), REQ-CI-045 (T2, T3), REQ-CI-046 (T1, T5), REQ-CI-047 (T4, T7), REQ-CI-048 (T8).

---

### Task 1: `ci/compute_matrix.py` — selection + row expansion (REQ-CI-046)

**Files:**
- Create: `ci/compute_matrix.py`
- Test: `ci/test_compute_matrix.py`

- [ ] **Step 1: Write the failing tests**

`ci/test_compute_matrix.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run (repo root): `python -m pytest ci/test_compute_matrix.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'ci.compute_matrix'`

- [ ] **Step 3: Implement `ci/compute_matrix.py`**

```python
"""Dynamic python-skill matrix from .github/ci/skills-matrix.json.

REQ-CI-046: on pull_request events only skills whose paths intersect the
PR diff are selected; shared-path hits and push/merge_group/dispatch/
schedule events select the full matrix. Fail-closed: any error computing
the selection exits non-zero, which fails the compute-matrix job, which
fails ci-required.

Profiles:
  pr             event-scoped selection, rows = entry x entry.os
  full           full selection, rows = entry x entry.os
  windows-canary full selection, one windows-2022 row per runnable entry
                 (nightly under-tagging safety net)
  python-compat  full selection, ubuntu-24.04 rows x --python-versions
                 (nightly py3.11/3.12 coverage; constraints dropped since
                 lockfiles are generated under 3.13)

Run:       python -m ci.compute_matrix --profile pr
Tested by: ci/test_compute_matrix.py
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = REPO_ROOT / ".github" / "ci" / "skills-matrix.json"
FULL_EVENTS = {"push", "merge_group", "workflow_dispatch", "schedule"}


def load_config(path: Path = MATRIX_PATH) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    for key in ("shared_paths", "defaults", "skills"):
        if key not in config:
            raise ValueError(f"skills-matrix.json missing top-level key {key!r}")
    return config


def runnable(config: dict) -> list[dict]:
    return [e for e in config["skills"] if e.get("ci") != "none"]


def shared_hit(paths: list[str], shared_paths: list[str]) -> bool:
    for pattern in shared_paths:
        if pattern.endswith("/**"):
            prefix = pattern[: -len("**")]
            if any(p.startswith(prefix) for p in paths):
                return True
        elif pattern in paths:
            return True
    return False


def changed_paths(base_ref: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"],
        check=True,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def select_skills(config: dict, event: str, paths: list[str]) -> list[dict]:
    entries = runnable(config)
    if event in FULL_EVENTS:
        return entries
    if shared_hit(paths, config["shared_paths"]):
        return entries
    return [
        e for e in entries
        if any(p.startswith(f"skills/{e['skill']}/") for p in paths)
    ]


def _row(
    entry: dict,
    os_name: str,
    defaults: dict,
    python_version: str = "3.13",
    include_constraints: bool = True,
) -> dict:
    return {
        "skill": entry["skill"],
        "os": os_name,
        "python_version": python_version,
        "extra": entry.get("extra", defaults.get("extra", "ci")),
        "constraints": entry.get("constraints", "") if include_constraints else "",
        "siblings": " ".join(entry.get("siblings", [])),
        "pytest_deselect": entry.get("pytest_deselect", ""),
        "pytest_workers": entry.get("pytest_workers", ""),
        "smoke": entry.get("smoke", ""),
        "spacy": "true" if entry.get("spacy") else "false",
        "hf_model": entry.get("hf_model", ""),
        "timeout": entry.get("timeout", defaults.get("timeout", 15)),
    }


def build_rows(
    entries: list[dict],
    config: dict,
    profile: str = "pr",
    python_versions: list[str] | None = None,
) -> list[dict]:
    defaults = config["defaults"]
    rows: list[dict] = []
    if profile in ("pr", "full"):
        for e in entries:
            for os_name in e.get("os", defaults["os"]):
                rows.append(_row(e, os_name, defaults))
    elif profile == "windows-canary":
        for e in entries:
            rows.append(_row(e, "windows-2022", defaults))
    elif profile == "python-compat":
        for e in entries:
            for version in python_versions or []:
                rows.append(
                    _row(e, "ubuntu-24.04", defaults, python_version=version,
                         include_constraints=False)
                )
    else:
        raise ValueError(f"unknown profile {profile!r}")
    return rows


def _write_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        print(f"{name}={value}")
        return
    with open(output_path, "a", encoding="utf-8") as f:
        f.write(f"{name}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        choices=["pr", "full", "windows-canary", "python-compat"],
        default="pr",
    )
    parser.add_argument("--python-versions", default="")
    parser.add_argument("--output-prefix", default="")
    args = parser.parse_args()

    config = load_config()
    if args.profile == "pr":
        event = os.environ.get("EVENT_NAME", "")
        if event == "pull_request":
            base_ref = os.environ.get("BASE_REF", "")
            if not base_ref:
                print("compute_matrix: BASE_REF unset on pull_request; failing closed")
                return 1
            selected = select_skills(config, event, changed_paths(base_ref))
        else:
            selected = select_skills(config, event or "push", [])
            if not selected:
                print("compute_matrix: zero skills on a full-matrix event; failing closed")
                return 1
    else:
        selected = runnable(config)
        if not selected:
            print("compute_matrix: zero runnable skills; failing closed")
            return 1

    versions = [v for v in args.python_versions.split(",") if v]
    rows = build_rows(selected, config, profile=args.profile, python_versions=versions)
    prefix = args.output_prefix
    _write_output(f"{prefix}matrix", json.dumps({"include": rows}))
    _write_output(f"{prefix}any_selected", "true" if rows else "false")
    print(f"compute_matrix [{args.profile}]: {len(rows)} rows "
          f"({len(selected)} skills selected)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest ci/test_compute_matrix.py -q`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add ci/compute_matrix.py ci/test_compute_matrix.py
git commit -m "ci: compute_matrix module — event-scoped dynamic matrix (REQ-CI-046)"
```

---

### Task 2: `.github/ci/skills-matrix.json` + registration lint (REQ-CI-040, REQ-CI-045)

**Files:**
- Create: `.github/ci/skills-matrix.json`
- Test: `ci/test_skills_matrix.py`

- [ ] **Step 1: Write the registry**

`.github/ci/skills-matrix.json` (content mirrors today's ci.yml matrix exactly — same skills, same overrides):

```json
{
  "shared_paths": [
    ".github/workflows/ci.yml",
    ".github/actions/**",
    ".github/ci/skills-matrix.json",
    "ci/**",
    "sibling_skills/**"
  ],
  "defaults": {
    "os": ["ubuntu-24.04", "macos-15", "windows-2022"],
    "extra": "ci",
    "timeout": 15
  },
  "skills": [
    { "skill": "book-qa", "constraints": "skills/book-qa/constraints.txt" },
    { "skill": "book-thesis" },
    { "skill": "book-knowledge" },
    { "skill": "book-review" },
    {
      "skill": "book-compose",
      "siblings": ["book-knowledge", "russellian-style", "book-review", "review-conductor"],
      "spacy": true,
      "pytest_deselect": "--deselect tests/test_sibling_skills.py::test_sibling_python_uses_skill_venv"
    },
    { "skill": "russellian-style", "spacy": true },
    { "skill": "feynman-style", "spacy": true },
    { "skill": "halmos" },
    { "skill": "iacr-review" },
    { "skill": "review-conductor" },
    {
      "skill": "neurosym-forge",
      "extra": "dev,semantic",
      "hf_model": "sentence-transformers/all-MiniLM-L6-v2",
      "pytest_workers": "auto",
      "timeout": 20
    },
    { "skill": "paragraph-weaver" },
    { "skill": "scrapling-fetch", "os": ["ubuntu-24.04"], "extra": "none", "smoke": "import" },
    { "skill": "syntopical-metabook", "os": ["ubuntu-24.04"], "extra": "none", "smoke": "import" },
    {
      "skill": "iacr-math-prose",
      "ci": "none",
      "reason": "reference/template-only skill; no Python package, no tests (AGENTS.md)"
    }
  ]
}
```

- [ ] **Step 2: Write the failing registration-lint tests**

`ci/test_skills_matrix.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they pass against the new JSON**

Run: `python -m pytest ci/test_skills_matrix.py -q`
Expected: all PASS (the JSON in Step 1 is complete). If `test_every_skill_dir_is_registered` fails, a skill exists that this plan missed — add it to the JSON, do not relax the test. Note: `skills/tests/` (shared cross-skill tests, no SKILL.md) is correctly excluded by the SKILL.md predicate; verify with `python -c "from pathlib import Path; print([p.name for p in Path('skills').iterdir() if p.is_dir() and not (p/'SKILL.md').exists()])"` — expected output includes only non-skill dirs.

- [ ] **Step 4: Commit**

```bash
git add .github/ci/skills-matrix.json ci/test_skills_matrix.py
git commit -m "ci: skills-matrix.json registry + registration lint (REQ-CI-040, REQ-CI-045)"
```

---

### Task 3: Port `check_windows_canary` to the JSON (REQ-CI-045)

**Files:**
- Modify: `ci/check_windows_canary.py`
- Modify: `ci/test_check_windows_canary.py`

- [ ] **Step 1: Rewrite the tests for the JSON source**

Replace the YAML fixture and parser tests in `ci/test_check_windows_canary.py` with:

```python
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
```

Keep `test_missing_canary_detection` exactly as it is today (it tests `skills_missing_canary`, which does not change). Replace `test_real_workflow_parses_and_repo_is_clean` with:

```python
def test_real_registry_parses_and_repo_is_clean():
    import json

    from ci.check_windows_canary import MATRIX_PATH, REPO_ROOT

    config = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    skills = full_pytest_matrix_skills(config)
    assert "neurosym-forge" in skills and "paragraph-weaver" in skills
    assert "syntopical-metabook" not in skills  # smoke-only entry
    assert skills_missing_canary(skills, REPO_ROOT / "skills") == []
```

Delete `test_parses_skill_axis_and_excludes_smoke_rows`, `test_include_only_full_pytest_row_is_detected`, `test_quoted_smoke_value_is_exempt`, and the `WORKFLOW_FIXTURE` block (they test the YAML parser being removed).

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `python -m pytest ci/test_check_windows_canary.py -q`
Expected: FAIL — `full_pytest_matrix_skills` still expects workflow text, and `MATRIX_PATH` does not exist.

- [ ] **Step 3: Rewrite `ci/check_windows_canary.py`**

Replace the module docstring's "Run as a check" block and the YAML parser. Keep `_MARKER_RE`, `skills_missing_canary`, and the `main()` error message verbatim. New selection logic:

```python
"""Windows-canary zero-marking guard.

The python-skill matrix runs `pytest -m windows_canary` on Windows. A matrix
skill whose tests/ contains zero windows_canary marks makes pytest exit 5
(no tests collected), reddening ci-required on every PR (the 2026-06-03
paragraph-weaver incident). This guard fails the cheap lint job instead,
naming the skill and the fix.

The skill list comes from .github/ci/skills-matrix.json (REQ-CI-045) —
smoke-only entries, linux-only entries, and ci:none entries never run
pytest on Windows and are exempt.

Run as a check:  python -m ci.check_windows_canary   (exits non-zero on violations)
Tested by:       ci/test_check_windows_canary.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = REPO_ROOT / ".github" / "ci" / "skills-matrix.json"

_MARKER_RE = re.compile(r"pytest\.mark\.windows_canary|pytestmark\s*=.*windows_canary")


def full_pytest_matrix_skills(config: dict) -> set[str]:
    """Skills that run full pytest on a windows-2022 leg."""
    selected: set[str] = set()
    for entry in config["skills"]:
        if entry.get("ci") == "none" or entry.get("smoke"):
            continue
        os_list = entry.get("os", config["defaults"]["os"])
        if "windows-2022" in os_list:
            selected.add(entry["skill"])
    return selected
```

`skills_missing_canary` stays unchanged. In `main()`, replace the workflow read with:

```python
def main() -> int:
    config = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    skills = full_pytest_matrix_skills(config)
    if not skills:
        print("check_windows_canary: ZERO windows-pytest skills in skills-matrix.json — registry drift; failing closed")
        return 1
```

(rest of `main()` unchanged — same `skills_missing_canary` call, same per-skill message, same OK line). Delete `WORKFLOW_PATH` and the old `full_pytest_matrix_skills` body.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest ci/test_check_windows_canary.py -q && python -m ci.check_windows_canary`
Expected: tests PASS; the check prints `check_windows_canary: OK (12 matrix skills all have marked tests)` and exits 0.

- [ ] **Step 5: Commit**

```bash
git add ci/check_windows_canary.py ci/test_check_windows_canary.py
git commit -m "ci: check_windows_canary reads skills-matrix.json instead of parsing ci.yml"
```

---

### Task 4: Composite actions — `symlink-siblings` + `setup-models` (REQ-CI-047)

**Files:**
- Create: `.github/actions/symlink-siblings/action.yml`
- Create: `.github/actions/setup-models/action.yml`
- Modify: `.github/dependabot.yml` (add the two new action dirs to the `github_actions` directories list, mirroring the existing `/.github/actions/setup-book-python` entry)

- [ ] **Step 1: Write `symlink-siblings`**

`.github/actions/symlink-siblings/action.yml` — the JS body is today's ci.yml block, with the template interpolation replaced by an env var (no behavior change, immune to injection):

```yaml
name: Symlink Sibling Skills
description: >
  Link sibling skills under ~/.claude/skills via Node fs.symlinkSync.
  `ln -sfn` requires Developer Mode (or admin) on Windows; the Node path
  works uniformly across ubuntu/macos/windows runners.

inputs:
  siblings:
    description: Space-separated sibling skill names to link
    required: true

runs:
  using: composite
  steps:
    - uses: actions/github-script@3a2844b7e9c422d3c10d287c895573f7108da1b3 # v9.0.0
      env:
        SIBLINGS: ${{ inputs.siblings }}
      with:
        script: |
          const { mkdirSync, symlinkSync, existsSync, rmSync } = require('fs');
          const { join } = require('path');
          const home = process.env.HOME || process.env.USERPROFILE;
          const target = join(home, '.claude', 'skills');
          mkdirSync(target, { recursive: true });
          const cwd = process.cwd();
          for (const s of process.env.SIBLINGS.split(/\s+/).filter(Boolean)) {
            const link = join(target, s);
            if (existsSync(link)) rmSync(link, { recursive: true, force: true });
            symlinkSync(join(cwd, 'skills', s), link, 'dir');
          }
```

- [ ] **Step 2: Write `setup-models`**

`.github/actions/setup-models/action.yml`. Key REQ-CI-047 properties: `cache/restore` + explicit `cache/save` right after a successful warm (so a warmed model survives later step failures), exponential backoff 15/30/60/120s, HF cache key preserved byte-for-byte from today's workflows (`hf-model-all-MiniLM-L6-v2-<OS>-v1`) so existing warm caches keep hitting:

```yaml
name: Setup Models
description: >
  Cache-and-warm ML model assets. The save happens in an explicit step
  immediately after a successful warm — NOT in actions/cache's post-job
  hook, which is skipped when the job fails. This breaks the cold-cache +
  flaky-network death spiral (REQ-CI-047): one successful warm anywhere
  persists the cache for every subsequent run on that OS.

inputs:
  spacy:
    description: Install the en_core_web_sm spaCy model ("true"/"false")
    required: false
    default: "false"
  hf-model:
    description: HuggingFace model id to warm into hf-cache ("" = skip)
    required: false
    default: ""

runs:
  using: composite
  steps:
    # ---------- spaCy model wheel ----------
    - name: restore spaCy model wheel cache
      if: inputs.spacy == 'true'
      id: restore-spacy
      uses: actions/cache/restore@27d5ce7f107fe9357f9df03efb73ab90386fccae # v5.0.5
      with:
        path: spacy-wheel
        key: spacy-model-en_core_web_sm-3.8.0
    # russellian-style's linters require the spaCy English model; the wheel is
    # installed with --no-deps so the click/typer-free [ci] extra is not
    # disturbed. `click` is added back because spaCy's top-level __init__
    # eagerly imports spacy.cli, which imports click. Pinned to the spaCy
    # 3.8.x model matching `spacy>=3.7,<4.0` in [ci].
    - name: install spaCy model (en_core_web_sm)
      if: inputs.spacy == 'true'
      shell: bash
      run: |
        retry() {
          for i in 1 2 3 4; do
            "$@" && return 0
            delay=$((15 * 2 ** (i - 1)))
            echo "attempt $i failed; retrying in ${delay}s" >&2
            sleep "$delay"
          done
          return 1
        }
        WHEEL_URL="https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"
        WHEEL="spacy-wheel/en_core_web_sm-3.8.0-py3-none-any.whl"
        mkdir -p spacy-wheel
        if [ ! -f "$WHEEL" ]; then
          retry curl -fsSL "$WHEEL_URL" -o "$WHEEL"
        fi
        retry python -m pip install click
        python -m pip install --no-deps "$WHEEL"
    - name: save spaCy model wheel cache
      if: inputs.spacy == 'true' && steps.restore-spacy.outputs.cache-hit != 'true'
      uses: actions/cache/save@27d5ce7f107fe9357f9df03efb73ab90386fccae # v5.0.5
      with:
        path: spacy-wheel
        key: spacy-model-en_core_web_sm-3.8.0

    # ---------- HuggingFace model ----------
    # Key preserved from the pre-composite workflows (basename of the model
    # id) so already-populated caches keep hitting. OS-scoped: the HF cache
    # uses symlinks on Linux/macOS but copies on Windows.
    - name: compute HF cache key
      if: inputs.hf-model != ''
      id: hf-key
      shell: bash
      env:
        HF_MODEL: ${{ inputs.hf-model }}
      run: echo "key=hf-model-$(basename "$HF_MODEL")-${{ runner.os }}-v1" >> "$GITHUB_OUTPUT"
    - name: restore HF model cache
      if: inputs.hf-model != ''
      id: restore-hf
      uses: actions/cache/restore@27d5ce7f107fe9357f9df03efb73ab90386fccae # v5.0.5
      with:
        path: hf-cache
        key: ${{ steps.hf-key.outputs.key }}
    - name: warm HF model cache
      if: inputs.hf-model != '' && steps.restore-hf.outputs.cache-hit != 'true'
      shell: bash
      env:
        HF_HOME: ${{ github.workspace }}/hf-cache
        HF_MODEL: ${{ inputs.hf-model }}
      run: |
        retry() {
          for i in 1 2 3 4; do
            "$@" && return 0
            delay=$((15 * 2 ** (i - 1)))
            echo "attempt $i failed; retrying in ${delay}s" >&2
            sleep "$delay"
          done
          return 1
        }
        retry python -c "import os; from huggingface_hub import snapshot_download; snapshot_download(os.environ['HF_MODEL'])"
    - name: save HF model cache
      if: inputs.hf-model != '' && steps.restore-hf.outputs.cache-hit != 'true'
      uses: actions/cache/save@27d5ce7f107fe9357f9df03efb73ab90386fccae # v5.0.5
      with:
        path: hf-cache
        key: ${{ steps.hf-key.outputs.key }}
```

- [ ] **Step 3: Add both action dirs to dependabot**

In `.github/dependabot.yml`, find the `github-actions` entry whose `directories` (or `directory`) list contains `/.github/actions/setup-book-python` and add `/.github/actions/symlink-siblings` and `/.github/actions/setup-models` alongside it, preserving the file's existing list style.

- [ ] **Step 4: Commit**

```bash
git add .github/actions/symlink-siblings .github/actions/setup-models .github/dependabot.yml
git commit -m "ci: symlink-siblings + setup-models composites; save model caches on warm success (REQ-CI-047)"
```

---

### Task 5: Rewrite `ci.yml` — compute-matrix + composites (REQ-CI-040, REQ-CI-046)

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add the `compute-matrix` job** (after `changes`)

```yaml
  # Dynamic python-skill matrix (REQ-CI-046). The skill registry lives in
  # .github/ci/skills-matrix.json; ci/compute_matrix.py scopes PR runs to the
  # skills the diff touches (shared-path hits and push/merge_group run the
  # full matrix). Fail-closed: a selection error fails this job, which fails
  # ci-required (it is in the require_success set).
  compute-matrix:
    name: compute python matrix
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    outputs:
      matrix: ${{ steps.compute.outputs.matrix }}
      any_selected: ${{ steps.compute.outputs.any_selected }}
    steps:
      - uses: actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10 # v6.0.3
        with:
          fetch-depth: 0   # compute_matrix diffs against origin/<base>
      - name: compute matrix from skills-matrix.json
        id: compute
        env:
          EVENT_NAME: ${{ github.event_name }}
          BASE_REF: ${{ github.base_ref }}
        run: python3 -m ci.compute_matrix --profile pr
```

- [ ] **Step 2: Replace the `python-skill-matrix` job's matrix and model steps**

The job header becomes:

```yaml
  python-skill-matrix:
    name: python-skill (${{ matrix.skill }} / ${{ matrix.os }})
    runs-on: ${{ matrix.os }}
    timeout-minutes: ${{ matrix.timeout }}
    needs: [compute-matrix]
    if: needs.compute-matrix.outputs.any_selected == 'true'
    strategy:
      fail-fast: false
      matrix: ${{ fromJSON(needs.compute-matrix.outputs.matrix) }}
```

The steps become (replacing the static `include:` table, the inline symlink JS, the two spaCy steps, the two HF steps):

```yaml
    steps:
      - uses: actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10 # v6.0.3
      - uses: ./.github/actions/setup-book-python
        with:
          python-version: ${{ matrix.python_version }}
          skill-path: skills/${{ matrix.skill }}
          extra: ${{ matrix.extra }}
          constraints: ${{ matrix.constraints }}
      - name: symlink siblings
        if: matrix.siblings != ''
        uses: ./.github/actions/symlink-siblings
        with:
          siblings: ${{ matrix.siblings }}
      - name: setup models (spaCy / HF as registered)
        uses: ./.github/actions/setup-models
        with:
          spacy: ${{ matrix.spacy }}
          hf-model: ${{ matrix.hf_model }}
      - name: import smoke
        if: matrix.smoke == 'import'
        working-directory: skills/${{ matrix.skill }}
        shell: bash
        run: python -c "import skill_api; print('import OK', skill_api.API_VERSION)"
      - name: pytest
        if: matrix.smoke != 'import'
        working-directory: skills/${{ matrix.skill }}
        shell: bash
        env:
          # hf_model legs only: read the warmed model cache, never the network.
          HF_HOME: ${{ matrix.hf_model != '' && format('{0}/hf-cache', github.workspace) || format('{0}/hf-unused', runner.temp) }}
          HF_HUB_OFFLINE: ${{ matrix.hf_model != '' && '1' || '0' }}
        run: |
          marker_filter=""
          if [ "${{ runner.os }}" = "Windows" ]; then
            marker_filter="-m windows_canary"
          fi
          # $marker_filter and the deselect/workers expansions are deliberately
          # unquoted: each must word-split into separate argv tokens. Empty
          # values expand to no args. SC2086 is intentional here.
          # shellcheck disable=SC2086
          if [ -n "${{ matrix.pytest_workers }}" ]; then
            python -m pytest tests/ -q --tb=short $marker_filter -n ${{ matrix.pytest_workers }} ${{ matrix.pytest_deselect }}
          else
            python -m pytest tests/ -q --tb=short $marker_filter ${{ matrix.pytest_deselect }}
          fi
```

Preserve the existing explanatory comment block above the job, replacing the sentence about `matrix.include` overrides with: "Per-skill configuration (extras, siblings, deselects, models) lives in .github/ci/skills-matrix.json."

- [ ] **Step 3: Retire the `python` paths-filter and re-gate `preflight`**

In the `changes` job: delete the `python:` filter block and the `python:` output (keep `rust:` exactly as is, including its comment). In `preflight`:

```yaml
    needs: [changes, compute-matrix]
    if: github.event_name != 'pull_request' || needs.changes.outputs.rust == 'true' || needs.compute-matrix.outputs.any_selected == 'true'
```

- [ ] **Step 4: Extend the `required` aggregator**

Add `compute-matrix` to its `needs:` list and to the always-run set:

```yaml
          COMPUTE_MATRIX: ${{ needs.compute-matrix.result }}
```
```bash
          require_success compute-matrix "$COMPUTE_MATRIX"
```

(alongside the existing `require_success lint` / `actionlint` / `ci-divergence-summary` lines; `python-skill-matrix` stays in `require_not_failed` — it legitimately skips on docs-only PRs).

- [ ] **Step 5: Sweep stale comments**

Update the actionlint job comment ("same pinned-tarball + SHA-verification install as ci-legacy's lint-workflow job" → drop the ci-legacy reference) and any other `ci-legacy` mention in ci.yml comments.

- [ ] **Step 6: Sanity-check the YAML locally**

Run: `python -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('.github/workflows/ci.yml').read_text(encoding='utf-8')); print('YAML OK')"`
Expected: `YAML OK`

- [ ] **Step 7: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: dynamic per-skill matrix via compute-matrix; model setup via composites (REQ-CI-046)"
```

---

### Task 6: Rewrite the nightly — composites, py-compat, ci-legacy coverage moves

**Files:**
- Modify: `.github/workflows/nightly-flake-drift.yml`

- [ ] **Step 1: Add a `compute-matrix` job to the nightly**

```yaml
  compute-matrix:
    name: compute nightly matrices
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    outputs:
      windows_matrix: ${{ steps.canary.outputs.windows_matrix }}
      compat_matrix: ${{ steps.compat.outputs.compat_matrix }}
    steps:
      - uses: actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10 # v6.0.3
      - name: windows-canary matrix (all runnable skills, windows-2022)
        id: canary
        run: python3 -m ci.compute_matrix --profile windows-canary --output-prefix windows_
      - name: python-compat matrix (all runnable skills, ubuntu x py3.11/3.12)
        id: compat
        run: python3 -m ci.compute_matrix --profile python-compat --python-versions 3.11,3.12 --output-prefix compat_
```

- [ ] **Step 2: Rewrite `windows-full-canary` on the dynamic matrix + composites**

Replace its static `matrix:` block with `matrix: ${{ fromJSON(needs.compute-matrix.outputs.windows_matrix) }}`, add `needs: [compute-matrix]`, and replace the inline symlink/spaCy/HF steps with the composites — same step sequence as ci.yml's matrix job (Task 5 Step 2) except the pytest step stays unfiltered:

```yaml
      - name: pytest (unfiltered)
        if: matrix.smoke != 'import'
        working-directory: skills/${{ matrix.skill }}
        shell: bash
        env:
          HF_HOME: ${{ matrix.hf_model != '' && format('{0}/hf-cache', github.workspace) || format('{0}/hf-unused', runner.temp) }}
          HF_HUB_OFFLINE: ${{ matrix.hf_model != '' && '1' || '0' }}
        run: python -m pytest tests/ -q --tb=short ${{ matrix.pytest_deselect }}
```

Keep the job's `timeout-minutes: 30` (nightly legs run unfiltered suites; do not use `matrix.timeout` here). Keep its explanatory comment. This also fixes a live drift bug: the static nightly list was missing feynman-style, halmos, iacr-review, and paragraph-weaver.

- [ ] **Step 3: Add the `python-compat` job** (coverage moved from ci-legacy's py3.11/3.12 legs)

```yaml
  # py3.11/3.12 compatibility legs (moved from ci-legacy on its retirement).
  # Skills declare requires-python >=3.11; PR-time CI tests 3.13 only, so this
  # nightly job is the only signal for the older interpreters. Linux-only;
  # constraints files are dropped by the python-compat profile (they are
  # generated under 3.13).
  python-compat:
    name: python-compat (${{ matrix.skill }} / py${{ matrix.python_version }})
    runs-on: ubuntu-24.04
    timeout-minutes: 30
    needs: [compute-matrix]
    strategy:
      fail-fast: false
      matrix: ${{ fromJSON(needs.compute-matrix.outputs.compat_matrix) }}
    steps:
      - uses: actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10 # v6.0.3
      - uses: ./.github/actions/setup-book-python
        with:
          python-version: ${{ matrix.python_version }}
          skill-path: skills/${{ matrix.skill }}
          extra: ${{ matrix.extra }}
      - name: symlink siblings
        if: matrix.siblings != ''
        uses: ./.github/actions/symlink-siblings
        with:
          siblings: ${{ matrix.siblings }}
      - name: setup models (spaCy / HF as registered)
        uses: ./.github/actions/setup-models
        with:
          spacy: ${{ matrix.spacy }}
          hf-model: ${{ matrix.hf_model }}
      - name: import smoke
        if: matrix.smoke == 'import'
        working-directory: skills/${{ matrix.skill }}
        shell: bash
        run: python -c "import skill_api; print('import OK', skill_api.API_VERSION)"
      - name: pytest
        if: matrix.smoke != 'import'
        working-directory: skills/${{ matrix.skill }}
        shell: bash
        env:
          HF_HOME: ${{ matrix.hf_model != '' && format('{0}/hf-cache', github.workspace) || format('{0}/hf-unused', runner.temp) }}
          HF_HUB_OFFLINE: ${{ matrix.hf_model != '' && '1' || '0' }}
        run: |
          # shellcheck disable=SC2086
          if [ -n "${{ matrix.pytest_workers }}" ]; then
            python -m pytest tests/ -q --tb=short -n ${{ matrix.pytest_workers }} ${{ matrix.pytest_deselect }}
          else
            python -m pytest tests/ -q --tb=short ${{ matrix.pytest_deselect }}
          fi
```

- [ ] **Step 4: Add `bermuda-example-pipeline`** (coverage moved from ci-legacy's `smoke-bermuda-pipeline`; preflight smokes the *verifier*, not the book-thesis pipeline on the worked example)

```yaml
  # End-to-end book-thesis pipeline on the worked example (moved from
  # ci-legacy on its retirement). Not covered by preflight, which smokes the
  # bermuda *verifier*, not the book-thesis compile/datalog chain.
  bermuda-example-pipeline:
    name: bermuda example pipeline (compile_thesis + datalog)
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10 # v6.0.3
      - uses: ./.github/actions/setup-book-python
        with:
          python-version: "3.13"
          skill-path: skills/book-thesis
      - name: compile_thesis
        run: python skills/book-thesis/scripts/compile_thesis.py examples/bermuda-manual bermuda-manual
      - name: consistency_cozo
        run: python skills/book-thesis/scripts/consistency_cozo.py examples/bermuda-manual
      - name: upload qa reports
        if: always()
        uses: actions/upload-artifact@<PIN># v4 — copy the SHA from onboarding-bench.yml if pinned there, else resolve via gh api
        with:
          name: bermuda-qa-reports
          path: |
            examples/bermuda-manual/qa/defects.json
            examples/bermuda-manual/qa/supports-defects.json
            examples/bermuda-manual/qa/datalog-defects.json
          if-no-files-found: warn
```

- [ ] **Step 5: Add `cljs-bermuda-test`** (coverage moved from ci-legacy; preflight builds the cljs release but never runs the cljs tests)

```yaml
  # shadow-cljs test compile + node run for the bermuda orchestrator (moved
  # from ci-legacy on its retirement). preflight's `make -C verifiers/bermuda
  # ci` builds the cljs release bundle but does not run the cljs test suite.
  cljs-bermuda-test:
    name: cljs-bermuda-test
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10 # v6.0.3
      - uses: actions/setup-node@<PIN># v4 — resolve SHA via gh api (see Conventions)
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: verifiers/bermuda/package-lock.json
      - uses: actions/setup-java@<PIN># v4 — resolve SHA via gh api (see Conventions)
        with:
          distribution: temurin
          java-version: "21"
      - name: npm install (lockfile-respecting)
        working-directory: verifiers/bermuda
        # `npm install` instead of `npm ci` — bermuda's lockfile sometimes
        # drifts from package.json across PRs in flight, and `npm ci` is
        # strict-fail there. The lockfile-cache key still keys on it.
        run: npm install --no-audit --no-fund
      - name: shadow-cljs compile + node test
        working-directory: verifiers/bermuda
        run: |
          npx shadow-cljs compile test
          node cljs-orchestrator/dist/test.js
```

- [ ] **Step 6: Extend `alert-on-failure`**

```yaml
    needs: [drift-check, windows-full-canary, python-compat, bermuda-example-pipeline, cljs-bermuda-test]
```

and in the issue body line "(flake check / preflight / windows canary)" append "/ python-compat / bermuda pipeline / cljs test".

- [ ] **Step 7: Sanity-check YAML + commit**

Run: `python -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('.github/workflows/nightly-flake-drift.yml').read_text(encoding='utf-8')); print('YAML OK')"`

```bash
git add .github/workflows/nightly-flake-drift.yml
git commit -m "nightly: dynamic matrices from skills-matrix.json; absorb ci-legacy's unique coverage"
```

---

### Task 7: Delete ci-legacy + update guard tests (REQ-CI-040, REQ-CI-047)

**Files:**
- Delete: `.github/workflows/ci-legacy.yml`
- Modify: `verifiers/osmotic_pressure/tests/test_ci_matrix_shape.py`
- Modify: `verifiers/bermuda/tests/test_axioms_lockstep.py` (the `test_ci_yaml_has_bermuda_z3_jobs` function)
- Modify: `verifiers/bermuda/Makefile` (smoke target deselect)

- [ ] **Step 1: Delete the workflow**

```bash
git rm .github/workflows/ci-legacy.yml
```

- [ ] **Step 2: Update `test_ci_matrix_shape.py`**

(a) Delete: `CI_LEGACY` constant, `_legacy_text()`, `test_legacy_bermuda_z3_job_name_not_misleading` (its target file is gone — the stubbed job it polices is dropped, not renamed).

(b) Add at top: `import json` and `MATRIX_JSON = REPO_ROOT / ".github" / "ci" / "skills-matrix.json"` plus

```python
def _matrix_config() -> dict:
    assert MATRIX_JSON.exists(), f"skills matrix registry not found at {MATRIX_JSON}"
    return json.loads(MATRIX_JSON.read_text(encoding="utf-8"))
```

(c) Re-point the three matrix-shape tests at the registry (same REQ IDs, new source of truth):

```python
def test_python_skill_matrix_has_three_oses():
    """REQ-CI-040: the default OS axis enumerates all three OSes."""
    assert _matrix_config()["defaults"]["os"] == [
        "ubuntu-24.04", "macos-15", "windows-2022",
    ]


def test_python_skill_include_overrides_are_in_skill_axis():
    """REQ-CI-040: override-carrying skills are full-coverage entries (no
    os restriction), so their overrides apply on every OS."""
    entries = {e["skill"]: e for e in _matrix_config()["skills"]}
    for skill in ("book-compose", "neurosym-forge"):
        entry = entries[skill]
        assert entry.get("ci") != "none", f"{skill} must be runnable"
        assert "os" not in entry, (
            f"{skill} must inherit the full default OS axis; an os override "
            "would silently drop matrix legs"
        )


def test_coverage_gap_skills_have_smoke_legs():
    """P2-matrix-coverage-gaps: scrapling-fetch + syntopical-metabook are
    covered by an install+import smoke leg, closing the zero-CI-signal gap
    on the highest supply-chain-risk skills."""
    entries = {e["skill"]: e for e in _matrix_config()["skills"]}
    for skill in ("scrapling-fetch", "syntopical-metabook"):
        assert entries[skill].get("smoke") == "import", (
            f"{skill} must be a `smoke: import` entry"
        )
```

(d) Add the REQ-CI-047 and REQ-CI-048 shape tests:

```python
SETUP_MODELS = REPO_ROOT / ".github" / "actions" / "setup-models" / "action.yml"


def test_model_caches_save_on_warm_success_not_post_job():
    """REQ-CI-047: setup-models uses explicit cache/restore + cache/save so a
    warmed model survives later step failures (the combined actions/cache
    post-job save is skipped on job failure — the 2026-06-04 Windows
    neurosym death spiral)."""
    text = SETUP_MODELS.read_text(encoding="utf-8")
    assert "actions/cache/restore@" in text, "setup-models must use cache/restore"
    assert "actions/cache/save@" in text, "setup-models must use explicit cache/save"
    assert "actions/cache@" not in text.replace(
        "actions/cache/restore@", ""
    ).replace("actions/cache/save@", ""), (
        "setup-models must not use the combined actions/cache (post-job save "
        "is skipped on job failure)"
    )


def test_python_matrix_uses_setup_models_composite():
    """REQ-CI-047: the matrix job consumes the composite, not inline steps."""
    text = _workflow_text()
    assert "./.github/actions/setup-models" in text


def test_budget_triggers_labeled_only():
    """REQ-CI-048: ci-budget must not trigger on opened/synchronize — the
    label gate made those runs permanent skipped-phantom noise (4-6 per PR
    push)."""
    text = _budget_text()
    on_block = text.split("\njobs:", 1)[0]
    assert "labeled" in on_block, "ci-budget must keep the labeled trigger"
    for noisy in ("opened", "synchronize"):
        assert noisy not in on_block, (
            f"ci-budget pull_request trigger must not include {noisy!r}"
        )
```

- [ ] **Step 3: Rewrite the bermuda z3 lockstep guard**

Read `verifiers/bermuda/tests/test_axioms_lockstep.py` first to match its existing YAML-loading idiom, then replace `test_ci_yaml_has_bermuda_z3_jobs` with:

```python
def test_ci_yaml_covers_bermuda_z3_build() -> None:
    """The repo CI must compile the bermuda verifier with the smt feature.
    Since ci-legacy's retirement this lives in ci.yml's cargo-test job
    (cargo test --features smt builds before testing)."""
    text = (BERMUDA_ROOT.parents[1] / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    jobs = yaml.safe_load(text)["jobs"]
    assert "cargo-test" in jobs, "cargo-test job missing from ci.yml"
    matrix = jobs["cargo-test"]["strategy"]["matrix"]
    assert "bermuda" in matrix["verifier"], "cargo-test matrix must include bermuda"
    run_lines = " ".join(
        step.get("run", "") for step in jobs["cargo-test"]["steps"]
    )
    assert "--features smt" in run_lines, "cargo-test must build with --features smt"
```

(adjust constant/import names to whatever the file actually uses).

- [ ] **Step 4: Drop the now-passing deselect from bermuda's Makefile**

In `verifiers/bermuda/Makefile`, remove the line
`--deselect tests/test_axioms_lockstep.py::test_ci_yaml_has_bermuda_z3_jobs \`
from the `smoke:` target (the other two deselects stay). This sub-Makefile is *not* covered by `scripts/ci-steps.txt` — the flake-drift check pins only the top-level preflight recipe lines, and `make -C verifiers/bermuda ci` is the unit of comparison there.

- [ ] **Step 5: Run the touched suites**

Run: `python -m pytest verifiers/osmotic_pressure/tests/test_ci_matrix_shape.py verifiers/bermuda/tests/test_axioms_lockstep.py -q`
Expected: all PASS (use the per-verifier venvs if system python lacks pyyaml: `verifiers/.../.venv` per AGENTS.md, or `pip install pyyaml`).

- [ ] **Step 6: Commit**

```bash
git add -A .github/workflows verifiers/osmotic_pressure/tests/test_ci_matrix_shape.py verifiers/bermuda/tests/test_axioms_lockstep.py verifiers/bermuda/Makefile
git commit -m "ci: retire ci-legacy; re-point matrix-shape guards at skills-matrix.json (REQ-CI-040/047/048)"
```

---

### Task 8: ci-budget trigger hygiene (REQ-CI-048)

**Files:**
- Modify: `.github/workflows/ci-budget.yml`

- [ ] **Step 1: Narrow the trigger**

```yaml
on:
  pull_request:
    types: [labeled]
  schedule:
    - cron: '0 9 * * 1'   # Mondays 09:00 UTC — weekly trend
  workflow_dispatch:
```

(only `opened, synchronize` are removed; the job-level label check stays as the second gate, and the schedule/dispatch paths are untouched).

- [ ] **Step 2: Verify the new guard test passes**

Run: `python -m pytest verifiers/osmotic_pressure/tests/test_ci_matrix_shape.py::test_budget_triggers_labeled_only -q`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci-budget.yml
git commit -m "ci-budget: trigger on labeled only — kill skipped-phantom runs (REQ-CI-048)"
```

---

### Task 9: Full local verification

- [ ] **Step 1: Run the whole ci/ suite**

Run (repo root): `python -m pytest ci/ -q`
Expected: all PASS

- [ ] **Step 2: Run the windows-canary guard**

Run: `python -m ci.check_windows_canary`
Expected: `check_windows_canary: OK (12 matrix skills all have marked tests)`

- [ ] **Step 3: Exercise compute_matrix end-to-end**

```bash
EVENT_NAME=push python -m ci.compute_matrix --profile pr            # expect 38 rows (12 skills x 3 OS + 2 smoke)
python -m ci.compute_matrix --profile windows-canary                 # expect 14 rows
python -m ci.compute_matrix --profile python-compat --python-versions 3.11,3.12   # expect 28 rows
```

Check the row counts in the printed summary line.

- [ ] **Step 4: actionlint on all workflows**

Download the pinned actionlint (same version as ci.yml's `ACTIONLINT_VERSION`) for the local platform and run `actionlint -color` at repo root. Expected: no findings. (On Windows: grab `actionlint_<ver>_windows_amd64.zip` from the GitHub release.)

- [ ] **Step 5: ruff + stale-reference grep**

```bash
ruff check ci/
grep -rn "ci-legacy" .github/ ci/ verifiers/ Makefile   # expect no hits outside docs archives
```

- [ ] **Step 6: Commit any fixes, then push and open the PR**

```bash
git push -u origin ci/consolidation
gh pr create --title "CI consolidation: dynamic skill matrix, model-cache hardening, ci-legacy retirement" --body-file openspec/changes/ci-consolidation/proposal.md
```

---

### Task 10: Remote verification (the "all green" gate)

- [ ] **Step 1: Confirm the PR runs the FULL matrix** (it touches shared paths) — `gh pr checks <num> --watch`. Expected: compute-matrix green, 38 python legs spawned, preflight + cargo-test green (the PR touches `.github/workflows/ci.yml`, which is in the rust filter), `ci-required` green.

- [ ] **Step 2: Confirm the HF fix held** — open the Windows neurosym-forge leg's log; the `setup-models` steps must show either `cache-hit` or a successful warm followed by `save HF model cache`.

- [ ] **Step 3: Scoping spot-check** — after merge, the next pure-docs or single-skill PR should show a reduced python matrix (verify on its checks page; or push a trivial `skills/halmos/`-only test branch and confirm exactly 3 python legs).

- [ ] **Step 4: Merge and watch main** — `gh run watch` the push run on main; `ci-required` green ends the "main is red" incident.

- [ ] **Step 5: Dispatch the nightly once** — `gh workflow run nightly-flake-drift.yml`, confirm windows-canary (14 legs), python-compat (28 legs), bermuda-example-pipeline, and cljs-bermuda-test all run. py-compat legs are advisory-by-alerting (a red leg files the tracking issue, it does not gate PRs); triage any 3.11/3.12 incompatibilities it surfaces as follow-ups.

- [ ] **Step 6: Archive the OpenSpec change** — per `openspec/README.md`: move `openspec/changes/ci-consolidation/` to `openspec/changes/archive/<date>-ci-consolidation/` and merge the spec delta into `openspec/specs/ci-platform/spec.md` (creating it from the tier4 baseline + this delta if the tier4 change archives first).
