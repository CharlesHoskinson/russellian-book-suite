"""Integration test: lint the actual repo README.md.

This is the merge gate. If any section of the README drifts under the lint, this test
fails and the merge is blocked. The unit tests in test_lint_readme.py use synthetic
fixtures; this test exercises the real README.
"""

from pathlib import Path

import pytest

from scripts.lint_readme import run_full_lint


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_README = _REPO_ROOT / "README.md"


@pytest.mark.skipif(not _README.exists(), reason="README.md not at repo root")
def test_real_readme_every_section_passes():
    """Every section of the repo README must pass the per-section lint gate."""
    results, exit_code = run_full_lint(_README)
    failures = [r for r in results if not r.passes]
    assert exit_code == 0, (
        f"{len(failures)} section(s) failed: "
        + ", ".join(f"{r.section.heading} (gating={r.gating_count})" for r in failures)
    )
