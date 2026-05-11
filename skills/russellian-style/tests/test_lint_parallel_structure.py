from pathlib import Path
from scripts.lint_parallel_structure import lint_parallel_structure


def test_flags_mixed_grammatical_openings():
    findings = lint_parallel_structure(Path("tests/fixtures/mixed_list_sample.md"))
    assert len(findings) >= 1
    flagged = findings[0]
    assert flagged["rule"] == "parallel-structure"
    assert "items" in flagged
    assert any(item["item"].startswith("Configuration") for item in flagged["items"])


def test_does_not_flag_parallel_lists():
    findings = lint_parallel_structure(Path("tests/fixtures/mixed_list_sample.md"))
    starts = [item["item"] for f in findings for item in f["items"]]
    assert "Install the package" not in starts or any(
        f["start_line"] > 6 for f in findings
    ) is False


def test_compliant_sample_has_no_findings():
    findings = lint_parallel_structure(Path("tests/fixtures/compliant_sample.md"))
    assert findings == []
