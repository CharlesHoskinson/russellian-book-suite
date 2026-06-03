import pytest
pytestmark = pytest.mark.windows_canary

from skill_api import lint_fragment, LintIssue, classify_linter, preserve_argument


def test_lint_fragment_runs_default_set():
    text = ("The phenomenological instantiation of electromagnetic propagation "
            "necessitates comprehensive reconceptualization of the theoretical superstructure.")
    issues = lint_fragment(text)
    assert all(isinstance(i, LintIssue) for i in issues)
    assert any(i.linter == "reading-grade" for i in issues)

def test_classify_linter():
    assert classify_linter("no-hedging") == "surface"
    assert classify_linter("preserve-argument") == "integrity"

def test_preserve_argument_reexported():
    r = preserve_argument("The cache stores results.", "The cache keeps your results around.")
    assert r.ok

def test_empty_text_returns_empty():
    assert lint_fragment("") == []
