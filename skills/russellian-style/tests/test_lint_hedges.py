from pathlib import Path
from scripts.lint_hedges import lint_hedges


def test_lint_hedges_detects_known_terms():
    path = Path("tests/fixtures/hedged_sample.md")
    findings = lint_hedges(path)
    terms = {f["term"] for f in findings}
    assert "might" in terms
    assert "seems" in terms
    assert "could" in terms
    assert "tends" in terms or "tends to" in terms
    assert "should probably" in terms
    assert "generally" in terms


def test_lint_hedges_records_line_numbers():
    findings = lint_hedges(Path("tests/fixtures/hedged_sample.md"))
    assert all(f["line"] >= 1 for f in findings)
    assert all(f["col"] >= 1 for f in findings)
    assert all("term" in f and "sentence" in f for f in findings)


def test_lint_hedges_returns_empty_for_compliant():
    findings = lint_hedges(Path("tests/fixtures/compliant_sample.md"))
    assert findings == []


def test_lint_hedges_skips_code_blocks():
    code_text = "```\nmight be valid python.\n```\n\nThe script works."
    tmp = Path("tests/fixtures/_codeblock_tmp.md")
    tmp.write_text(code_text, encoding="utf-8")
    try:
        findings = lint_hedges(tmp)
        assert findings == []
    finally:
        tmp.unlink()


def test_lint_hedges_skips_capitalized_may_as_month_name(tmp_path):
    text = "# Sample\n\nThe legislature met on May 22, 1968."
    f = tmp_path / "month.md"
    f.write_text(text, encoding="utf-8")
    findings = lint_hedges(f)
    assert findings == []


def test_lint_hedges_skips_capitalized_may_as_surname(tmp_path):
    text = "# Sample\n\nHenry May arrived from Bermuda in 1593."
    f = tmp_path / "surname.md"
    f.write_text(text, encoding="utf-8")
    findings = lint_hedges(f)
    assert findings == []


def test_lint_hedges_still_catches_lowercase_may(tmp_path):
    text = "# Sample\n\nThe script may fail under heavy load."
    f = tmp_path / "hedge.md"
    f.write_text(text, encoding="utf-8")
    findings = lint_hedges(f)
    assert any(f["term"] == "may" for f in findings)
