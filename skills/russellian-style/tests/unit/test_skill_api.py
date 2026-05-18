"""Unit tests for the russellian-style public skill_api surface (IF-RS-1)."""
from __future__ import annotations

from pathlib import Path


import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from skill_api import (
    lint_fragment,
    LintIssue,
    API_VERSION,
)


# ---------------------------------------------------------------------------
# IF-RS-0: API surface
# ---------------------------------------------------------------------------

def test_api_version():
    assert API_VERSION == (0, 1)


# ---------------------------------------------------------------------------
# IF-RS-1: lint_fragment
# ---------------------------------------------------------------------------

# A hedged sentence — should trigger no-hedging
HEDGED_TEXT = "The system might work correctly under certain conditions."

# A sentence with passive voice
PASSIVE_TEXT = "The protocol is verified by the validator."

# Clean prose — no obvious violations
CLEAN_TEXT = "The validator checks every transaction against the ledger."


def test_lint_fragment_returns_list():
    issues = lint_fragment(HEDGED_TEXT)
    assert isinstance(issues, list)


def test_lint_fragment_hedging_detected():
    issues = lint_fragment(HEDGED_TEXT)
    assert len(issues) > 0
    assert all(isinstance(i, LintIssue) for i in issues)


def test_lint_fragment_issue_has_line_and_col():
    issues = lint_fragment(HEDGED_TEXT)
    assert len(issues) > 0
    for issue in issues:
        assert isinstance(issue.line, int) and issue.line >= 1
        assert isinstance(issue.col, int) and issue.col >= 1


def test_lint_fragment_issue_has_linter_and_message():
    issues = lint_fragment(HEDGED_TEXT)
    assert len(issues) > 0
    for issue in issues:
        assert issue.linter != ""
        assert issue.message != ""


def test_lint_fragment_specific_linter_limits_results():
    # Running only no-hedging should not return passive-voice results
    all_issues = lint_fragment(PASSIVE_TEXT + " " + HEDGED_TEXT)
    hedging_only = lint_fragment(PASSIVE_TEXT + " " + HEDGED_TEXT, linters=["no-hedging"])
    linter_names = {i.linter for i in hedging_only}
    assert linter_names <= {"no-hedging"}
    # The subset should be <= the full set in count
    assert len(hedging_only) <= len(all_issues)


def test_lint_fragment_unknown_linter_returns_empty():
    issues = lint_fragment(HEDGED_TEXT, linters=["nonexistent-linter"])
    assert issues == []


def test_lint_fragment_empty_text_returns_empty():
    issues = lint_fragment("")
    assert issues == []
