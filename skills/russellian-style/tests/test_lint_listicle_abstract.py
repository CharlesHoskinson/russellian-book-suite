import pytest

pytestmark = pytest.mark.windows_canary

from scripts.lint_listicle_abstract import lint_listicle_abstract


LISTICLE_PHRASE = """# Sample

The manual rests on six premises:
The world is round.
"""

LISTICLE_ENUM = """# Sample

Some intro text.

1. Bermuda occupies 53.3 square kilometers of land in mid-Atlantic isolation.
2. Bermuda lies 1,040 kilometers from the nearest mainland.
3. Bermuda has no rivers and no aquifer.
4. Bermuda has a tropical climate at unusual latitude.
"""

CLEAN = """# Sample

The script provisions the server. Logs persist to disk every minute.
The daemon loads configurations at startup and rebuilds them on SIGHUP.
"""


def test_flags_rests_on_n_premises_phrase(tmp_path):
    f = tmp_path / "phrase.md"
    f.write_text(LISTICLE_PHRASE, encoding="utf-8")
    findings = lint_listicle_abstract(f)
    assert any(x["rule"] == "listicle-abstract" for x in findings)
    assert any("rests on six premises" in x["snippet"].lower() for x in findings)


def test_flags_anaphoric_enumeration(tmp_path):
    f = tmp_path / "enum.md"
    f.write_text(LISTICLE_ENUM, encoding="utf-8")
    findings = lint_listicle_abstract(f)
    assert any(x["rule"] == "listicle-anaphora" for x in findings)
    assert any("Bermuda" in x["snippet"] for x in findings)


def test_clean_prose_returns_no_findings(tmp_path):
    f = tmp_path / "clean.md"
    f.write_text(CLEAN, encoding="utf-8")
    findings = lint_listicle_abstract(f)
    assert findings == []


def test_short_anaphoric_run_not_flagged(tmp_path):
    text = """# Sample

1. Bermuda is in the Atlantic.
2. Bermuda has 64,000 residents.
3. The economy is split between tourism and finance.
"""
    f = tmp_path / "two.md"
    f.write_text(text, encoding="utf-8")
    findings = lint_listicle_abstract(f)
    assert not any(x["rule"] == "listicle-anaphora" for x in findings)
