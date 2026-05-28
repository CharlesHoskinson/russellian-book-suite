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


def test_advisory_severity_only(tmp_path):
    text = "O'er the lea, O Reader, the storm raged as if in sympathy with our sorrow."
    findings = lint_ornament(_write(tmp_path, text))
    assert findings, "expect at least one finding"
    assert all(f["severity"] == "advisory" for f in findings)


def test_determinism(tmp_path):
    text = "O'er the lea. O Reader, attend."
    p = _write(tmp_path, text)
    assert lint_ornament(p) == lint_ornament(p)
