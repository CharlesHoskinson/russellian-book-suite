from pathlib import Path
from scripts.lint_sentence_rhythm import lint_sentence_rhythm


UNIFORM_RHYTHM = """# Sample

Bermuda lies in the Atlantic Ocean far from the mainland coast. Bermuda has a temperate climate moderated by the Gulf Stream current. Bermuda contains roughly sixty thousand residents in fifty square kilometres. Bermuda imports nearly all its food and consumer goods. Bermuda exports financial services through its insurance market.
"""

REPEATED_OPENING = """# Sample

Bermuda lies in the Atlantic. The skies cleared. Bermuda has fifty kilometres of coast. Things changed quickly. Bermuda exports services. We adapted.

Bermuda saw growth. Bermuda saw decline. Bermuda saw recovery. Bermuda saw growth again.
"""

VARIED = """# Sample

Bermuda is small. The archipelago covers fifty-three square kilometres of land scattered across more than a hundred islands and rocks. Climate moderates the seasons. Although hurricanes cross from June through November, the main currents from the Gulf Stream keep mean temperatures higher than the latitude alone would predict.
"""


def test_flags_uniform_word_count_run(tmp_path):
    f = tmp_path / "uniform.md"
    f.write_text(UNIFORM_RHYTHM, encoding="utf-8")
    findings = lint_sentence_rhythm(f)
    assert any(x["rule"] == "rhythm-uniform-length" for x in findings)


def test_flags_repeated_sentence_openings(tmp_path):
    f = tmp_path / "repeat.md"
    f.write_text(REPEATED_OPENING, encoding="utf-8")
    findings = lint_sentence_rhythm(f)
    assert any(x["rule"] == "rhythm-repeated-opening" for x in findings)
    assert any(x.get("first_word", "").lower() == "bermuda" for x in findings)


def test_varied_prose_passes(tmp_path):
    f = tmp_path / "varied.md"
    f.write_text(VARIED, encoding="utf-8")
    findings = lint_sentence_rhythm(f)
    assert findings == []
