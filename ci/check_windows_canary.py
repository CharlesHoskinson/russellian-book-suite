"""Windows-canary zero-marking guard.

The python-skill matrix runs `pytest -m windows_canary` on Windows. A matrix
skill whose tests/ contains zero windows_canary marks makes pytest exit 5
(no tests collected), reddening ci-required on every PR (the 2026-06-03
paragraph-weaver incident). This guard fails the cheap lint job instead,
naming the skill and the fix.

Smoke-only matrix rows (`smoke: import`) never run pytest and are exempt.

Run as a check:  python -m ci.check_windows_canary   (exits non-zero on violations)
Tested by:       ci/test_check_windows_canary.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"

_MARKER_RE = re.compile(r"pytest\.mark\.windows_canary|pytestmark\s*=.*windows_canary")


def full_pytest_matrix_skills(workflow_text: str) -> set[str]:
    """Skills on the matrix `skill:` axis (full pytest on Windows).

    Include-only rows are added by `include:` entries; any row carrying
    `smoke: import` is exempt (and removed even if it also sits on the axis).
    """
    lines = workflow_text.splitlines()
    axis: set[str] = set()
    in_skill_axis = False
    skill_indent = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"^skill:\s*$", stripped):
            in_skill_axis = True
            skill_indent = len(line) - len(line.lstrip())
            continue
        if in_skill_axis:
            indent = len(line) - len(line.lstrip())
            m = re.match(r"^-\s*([A-Za-z0-9_-]+)\s*$", stripped)
            if m and indent > skill_indent:
                axis.add(m.group(1))
                continue
            if stripped and indent <= skill_indent:
                in_skill_axis = False
    # Walk include rows: a `- skill: X` bullet runs full pytest on Windows
    # UNLESS its sibling keys (same indent, until the next `- `) carry
    # `smoke: import`. Non-smoke include rows are added to the result even when
    # they never appear on the `skill:` axis (a partial-drift gap); smoke rows
    # go to the exempt set and are subtracted (covering axis + include alike).
    # Smoke values may be bare or quoted (`import` / 'import' / "import").
    include_nonsmoke: set[str] = set()
    smoke: set[str] = set()
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)-\s*skill:\s*([A-Za-z0-9_-]+)\s*$", line)
        if not m:
            continue
        row_indent, skill = len(m.group(1)), m.group(2)
        is_smoke = False
        for j in range(i + 1, len(lines)):
            nxt = lines[j]
            if not nxt.strip():
                continue
            nxt_indent = len(nxt) - len(nxt.lstrip())
            if nxt_indent <= row_indent or nxt.lstrip().startswith("- "):
                break
            if re.match(r"^smoke:\s*['\"]?import['\"]?\s*$", nxt.strip()):
                is_smoke = True
                break
        if is_smoke:
            smoke.add(skill)
        else:
            include_nonsmoke.add(skill)
    return (axis | include_nonsmoke) - smoke


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
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    skills = full_pytest_matrix_skills(text)
    if not skills:
        print("check_windows_canary: parsed ZERO matrix skills from ci.yml — parser drift; failing closed")
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
