"""Cites REQ-VOICE-020, REQ-VOICE-021.

Filename is test_humanity_token_closers.py (NOT test_lint_*) so the conftest's
spaCy-absent collect_ignore_glob does not silently skip it in CI.
"""
import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path

from scripts.lint_humanity_token_closers import lint_humanity_token_closers


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    return p


# Positive: closers the v3 critique named as chassis aphorisms.
def test_civilisation_closer_flagged(tmp_path):
    # v3 snails essay paragraph 4 closer (paraphrase): humanity-token "we" +
    # token "civilisation", 23 words, no concrete-instance marker, no first-person.
    text = (
        "Gutenberg pulled a sheet of damp paper from the press.\n\n"
        "We have built whole industries on the difficulty of doing what the snail "
        "does without a thought, and we have called the result civilisation."
    )
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    assert len(findings) == 1
    assert findings[0]["rule"] == "humanity-token-closer"
    assert findings[0]["severity"] == "advisory"


def test_men_universal_closer_flagged(tmp_path):
    text = (
        "Consider the question of disputed property lines.\n\n"
        "Men spend their fiercest passions disputing the ownership of ground they did not make."
    )
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    assert len(findings) == 1


def test_nature_universal_closer_flagged(tmp_path):
    text = (
        "The thrush carries the shell to the anvil stone.\n\n"
        "Nature is sparing with most things and spends its ironies freely."
    )
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    assert len(findings) == 1


def test_compact_aphorism_at_word_floor_flagged(tmp_path):
    # 8 words. The first draft's lower bound of 8 misses 8-word closers if we use ≥; use ≥6.
    text = (
        "The contest with the snail is more even than the gardener admits.\n\n"
        "Slowness is, for most of us, a strength."
    )
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    assert len(findings) == 1


def test_long_russell_closer_within_cap_flagged(tmp_path):
    # 27 words. The first draft's 18-word cap missed Russell's characteristic 20-30 word closers.
    text = (
        "The snail keeps no theology and holds no opinion for which it would kill a neighbour.\n\n"
        "I do not offer the snail as a model of every virtue but in one matter "
        "of not being certain past the evidence it improves upon the larger part of mankind."
    )
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    # The closer contains "I" — first-person-singular subtraction disqualifies it.
    # This documents that the rebuilt linter does NOT flag testimony closers.
    assert findings == []


def test_closer_above_28_word_cap_not_flagged(tmp_path):
    # 31 words: above the rebuilt cap. The over-long sweeping closer lands in the
    # burstiness layer, not in this advisory.
    long_closer = (
        "The slowest of creatures is among the best travelled, carried to its empire "
        "asleep on the feet of wading ducks across oceans it could never have crossed "
        "by its own slow motion alone."
    )
    text = "Darwin made the observation.\n\n" + long_closer
    assert len(long_closer.split()) >= 29  # sanity-check the fixture
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    assert findings == []


def test_closer_with_concrete_instance_marker_not_flagged(tmp_path):
    # Capitalised non-initial word ("Bernoulli") = concrete-instance marker.
    text = (
        "The shell records the seasons.\n\n"
        "The geometer Bernoulli earns the spiral by labour and dies."
    )
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    assert findings == []


def test_closer_with_year_not_flagged(tmp_path):
    text = (
        "Mainz was the centre of the new craft.\n\n"
        "By 1452 the press had multiplied book production by orders of magnitude."
    )
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    assert findings == []


def test_closer_with_first_person_singular_not_flagged(tmp_path):
    text = (
        "The reader will perhaps allow a personal note.\n\n"
        "I have known arguments conducted with less attention than the snail gives a leaf."
    )
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    assert findings == []


def test_plain_descriptive_closer_not_flagged(tmp_path):
    text = (
        "Watch the crossing.\n\n"
        "The crossing finished without an audience and without hurry on the wet flagstone."
    )
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    # No humanity token. Should not flag.
    assert findings == []


def test_quoted_closer_excluded(tmp_path):
    # The humanity-token closer lives inside a double-quoted span; strip_quotes
    # removes it before scanning.
    text = 'Russell once said, "We have invented a hundred narcotics against tedium."'
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    assert findings == []


def test_blockquote_closer_excluded(tmp_path):
    text = "Russell once said:\n\n> We have invented a hundred narcotics against tedium.\n"
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    assert findings == []


def test_determinism(tmp_path):
    text = (
        "The snail withdraws.\n\n"
        "We have invented a hundred narcotics against tedium."
    )
    p = _write(tmp_path, text)
    assert lint_humanity_token_closers(p) == lint_humanity_token_closers(p)
