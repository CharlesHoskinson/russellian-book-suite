"""Cites REQ-VOICE-013, REQ-VOICE-014, REQ-VOICE-015.

Named test_ornament.py (NOT test_lint_*) so the conftest's spaCy-absent
collect_ignore_glob does not silently skip it in CI.
"""
import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path

from scripts.lint_ornament import lint_ornament


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_archaic_diction_flagged(tmp_path):
    findings = lint_ornament(_write(tmp_path, "He gazed o'er the lea where 'tis ever still."))
    markers = {f["marker"] for f in findings}
    assert "archaic_diction" in markers
    assert all(f["severity"] == "advisory" for f in findings)


def test_apostrophe_flagged_when_unquoted(tmp_path):
    findings = lint_ornament(_write(tmp_path, "O Reader, attend. The argument proceeds by cases."))
    assert any(f["marker"] == "apostrophe" for f in findings)


def test_apostrophe_inside_quotes_not_flagged(tmp_path):
    findings = lint_ornament(_write(tmp_path, 'He cried, "O Reader, attend!" The argument proceeds.'))
    assert not any(f["marker"] == "apostrophe" for f in findings)


def test_o_prefixed_technical_term_not_flagged(tmp_path):
    # "O Ring" at sentence start must not trip the apostrophe pattern; only "O X," or
    # "O X!" (addressee form) qualifies.
    findings = lint_ornament(_write(tmp_path, "O Ring seal failures are common in low temperatures."))
    assert not any(f["marker"] == "apostrophe" for f in findings)


def test_archaism_inside_blockquote_not_flagged(tmp_path):
    text = "Russell wrote plainly. Longfellow did not:\n\n> O'er the lea where 'tis ever still.\n\nThe distinction is the point."
    findings = lint_ornament(_write(tmp_path, text))
    assert not any(f["marker"] == "archaic_diction" for f in findings)


def test_clean_russell_sentence_produces_no_findings(tmp_path):
    text = (
        "Philosophy is to be studied not for definite answers but for the questions themselves. "
        "The argument proceeds by cases. We begin with the table in this room."
    )
    findings = lint_ornament(_write(tmp_path, text))
    assert findings == []


def test_adverb_amplified_verb_flagged(tmp_path):
    findings = lint_ornament(_write(tmp_path, "He loudly roared and savagely glared at the crowd."))
    markers = {f["marker"] for f in findings}
    assert "adverb_amplified_verb" in markers


def test_non_adverb_ly_words_not_flagged(tmp_path):
    # 'gully', 'family', 'Italy' all end in 'ly' but are not adverbs. The closed
    # adverb list excludes them.
    text = "The gully roared with spring melt and the family blazed with new vigour."
    findings = lint_ornament(_write(tmp_path, text))
    assert not any(f["marker"] == "adverb_amplified_verb" for f in findings)


def test_adjective_stacking_flagged(tmp_path):
    findings = lint_ornament(_write(tmp_path, "Her beautiful, lovely smile filled the room."))
    assert any(f["marker"] == "adjective_stacking" for f in findings)


def test_adjective_stacking_does_not_cross_lines(tmp_path):
    # Two evaluative adjectives at end of one line and start of another are
    # different sentences; the linter must not flag them as stacked.
    text = "The argument is radiant\nTender treatment of exceptions follows in section three."
    findings = lint_ornament(_write(tmp_path, text))
    assert not any(f["marker"] == "adjective_stacking" for f in findings)


def test_abstract_emotion_word_flagged_mid_sentence(tmp_path):
    findings = lint_ornament(_write(tmp_path, "The chapter ends with sorrow, then turns."))
    assert any(f["marker"] == "abstract_emotion_word" for f in findings)


def test_abstract_emotion_word_at_end_of_file_flagged(tmp_path):
    # A markdown file may end with no trailing newline or punctuation.
    p = tmp_path / "no_trailing.md"
    p.write_text("The chapter ends with sorrow", encoding="utf-8")
    findings = lint_ornament(p)
    assert any(f["marker"] == "abstract_emotion_word" for f in findings)


def test_nature_mirrors_mood_flagged(tmp_path):
    findings = lint_ornament(_write(tmp_path, "The storm raged, as if in sympathy with our argument."))
    assert any(f["marker"] == "nature_mirrors_mood" for f in findings)


def test_advisory_severity_only(tmp_path):
    text = "O'er the lea, O Reader, the storm raged as if in sympathy with our sorrow."
    findings = lint_ornament(_write(tmp_path, text))
    assert findings, "expect at least one finding"
    assert all(f["severity"] == "advisory" for f in findings)


def test_total_instances_consumable_by_voice_eval(tmp_path):
    # voice_eval._signals does len(fn(path)) — the linter must emit one finding per
    # match instance so per-1000 density scales with ornament frequency.
    one = lint_ornament(_write(tmp_path, "He gazed o'er the lea."))
    many = lint_ornament(_write(tmp_path, "He gazed o'er the lea and o'er the brook and o'er the hill."))
    assert len(many) > len(one)


def test_determinism(tmp_path):
    text = "O'er the lea. O Reader, attend."
    p = _write(tmp_path, text)
    assert lint_ornament(p) == lint_ornament(p)
