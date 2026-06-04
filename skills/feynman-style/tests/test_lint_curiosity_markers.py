import pytest
pytestmark = pytest.mark.windows_canary

from pathlib import Path
from scripts.lint_curiosity_markers import lint_curiosity_markers, count_markers


def test_counts_curiosity_phrases():
    text = "The funny thing is, nobody really knows why. Here's the puzzle that bugged everyone."
    assert count_markers(text) >= 2

def test_flags_passage_without_curiosity(tmp_path):
    md = tmp_path / "flat.md"
    md.write_text(
        "The procedure runs in three stages. Each stage validates its input. "
        "The final stage emits the result. The result is stored in the ledger. "
        "Downstream consumers read the ledger entry directly.\n",
        encoding="utf-8",
    )
    findings = lint_curiosity_markers(md)
    assert any(f["rule"] == "curiosity-absent" for f in findings)


def test_rhetorical_question_is_curious(tmp_path):
    # Regression: a paragraph whose curiosity is carried by a rhetorical question
    # (not a whitelisted phrase) must not be flagged curiosity-absent.
    md = tmp_path / "q.md"
    md.write_text(
        "How do you stop wishful reading from creeping in? You replace opinions with gates, "
        "and you make every later step earn its place by clearing the one before it, so the "
        "pipeline can never conclude more than its own measurements actually support.\n",
        encoding="utf-8",
    )
    assert not any(f["rule"] == "curiosity-absent" for f in lint_curiosity_markers(md))
