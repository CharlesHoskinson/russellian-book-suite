import pytest
pytestmark = pytest.mark.windows_canary

from pathlib import Path
from scripts.lint_reading_grade import lint_reading_grade, _syllables, _fk_grade


def test_syllable_counter_basic():
    assert _syllables("cat") == 1
    assert _syllables("running") == 2
    assert _syllables("intuition") == 4

def test_fk_grade_monotonic():
    easy = _fk_grade(words=10, sentences=1, syllables=12)
    hard = _fk_grade(words=30, sentences=1, syllables=70)
    assert hard > easy

def test_flags_dense_sentence(tmp_path):
    md = tmp_path / "hard.md"
    md.write_text(
        "The phenomenological instantiation of electromagnetic propagation "
        "necessitates a comprehensive reconceptualization of the underlying "
        "theoretical superstructure governing particulate interactions.\n",
        encoding="utf-8",
    )
    findings = lint_reading_grade(md, max_grade=12)
    assert findings
    assert findings[0]["rule"] == "reading-grade"
    assert findings[0]["grade"] > 12

def test_passes_plain_sentence(tmp_path):
    md = tmp_path / "plain.md"
    md.write_text("Atoms are little things that jiggle. The hotter it is, the more they jiggle.\n", encoding="utf-8")
    assert lint_reading_grade(md, max_grade=12) == []
