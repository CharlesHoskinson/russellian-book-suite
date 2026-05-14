"""Regression: the bad Bitcoin sample fires the new lint; the good one is silent."""
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "before_after"


def test_bitcoin_staccato_fires_expected_rules():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "bitcoin_staccato.md")
    rules = {f["rule"] for f in findings}
    assert "staccato-paragraph-run" in rules
    assert "negation-affirmation-template" in rules
    assert "this-is-conclusion-overuse" in rules
    assert "abstract-subject-run" in rules


def test_bitcoin_russellian_silent_under_ai_staccato():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "bitcoin_russellian.md")
    assert findings == [], f"expected no findings; got {findings}"


def test_bitcoin_russellian_silent_under_negative_linters():
    """Sanity check: the good sample passes all six negative linters too.

    Budget: at most 4 findings across all six linters combined.
    """
    from scripts.lint_hedges import lint_hedges
    from scripts.lint_passive_voice import lint_passive_voice
    from scripts.lint_signal_density import lint_signal_density
    from scripts.lint_parallel_structure import lint_parallel_structure
    from scripts.lint_sentence_rhythm import lint_sentence_rhythm
    from scripts.lint_listicle_abstract import lint_listicle_abstract
    sample = FIXTURES / "bitcoin_russellian.md"
    findings = (
        lint_hedges(sample)
        + lint_passive_voice(sample)
        + lint_signal_density(sample)
        + lint_parallel_structure(sample)
        + lint_sentence_rhythm(sample)
        + lint_listicle_abstract(sample)
    )
    # The negative-linter suite is strict; the good sample is allowed at most
    # a small number of findings.
    assert len(findings) <= 4, f"too many negative findings: {findings}"
