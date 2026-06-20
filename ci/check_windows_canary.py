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


def skills_missing_canary(skills: set[str], skills_dir: Path) -> list[str]:
    """Skills whose tests/ tree contains no windows_canary marker."""
    missing: list[str] = []
    for skill in sorted(skills):
        tests_dir = skills_dir / skill / "tests"
        marked = any(
            _MARKER_RE.search(p.read_text(encoding="utf-8", errors="replace"))
            for p in tests_dir.rglob("test_*.py")
        ) if tests_dir.is_dir() else False
        if not marked:
            missing.append(skill)
    return missing


def main() -> int:
    config = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    skills = full_pytest_matrix_skills(config)
    if not skills:
        print("check_windows_canary: ZERO windows-pytest skills in skills-matrix.json — registry drift; failing closed")
        return 1
    missing = skills_missing_canary(skills, REPO_ROOT / "skills")
    if missing:
        for skill in missing:
            print(
                f"skills/{skill}/tests has NO windows_canary-marked test. The Windows "
                f"matrix leg runs `pytest -m windows_canary` and will exit 5 (no tests "
                f"collected). Fix: add `import pytest` + `pytestmark = pytest.mark."
                f"windows_canary` to its test files (see skills/feynman-style/tests for "
                f"the pattern) and register the marker in pyproject.toml."
            )
        return 1
    print(f"check_windows_canary: OK ({len(skills)} matrix skills all have marked tests)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
