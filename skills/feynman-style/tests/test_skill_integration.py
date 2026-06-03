import pytest
pytestmark = pytest.mark.windows_canary

from pathlib import Path
from skill_api import lint_fragment, classify_linter, preserve_argument

RUSSELL = Path("tests/fixtures/russell_output.md").read_text(encoding="utf-8")
FEYNMAN = (
    "Think of the cache as a notepad that stores results. "
    "The first time you ask a question, it works out the answer and jots it down. "
    "Ask the same thing again and it reads it back from disk — "
    "so you skip the network call entirely."
)


def test_a_feynman_budgets_met():
    issues = lint_fragment(FEYNMAN)
    grades = [i for i in issues if i.linter == "reading-grade"]
    assert grades == []  # warmed prose is under the grade budget


def test_b_argument_preserved():
    report = preserve_argument(RUSSELL, FEYNMAN)
    assert report.ok, report.violations


def test_c_surface_russell_checks_are_suppressed():
    # The rhetorical question + contractions in FEYNMAN are surface-class and
    # must be classified for suppression on feynman-final text.
    assert classify_linter("no-hedging") == "surface"
    assert classify_linter("signal-density") == "surface"
    # Integrity checks remain enforced.
    assert classify_linter("preserve-argument") == "integrity"
