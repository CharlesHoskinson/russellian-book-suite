from pathlib import Path
from scripts.style_pass_report import build_report, write_report


def test_build_report_aggregates_all_linters():
    report = build_report(Path("tests/fixtures/hedged_sample.md"))
    assert "Style Pass Report" in report
    assert "no-hedging" in report
    assert "hedge_count:" in report


def test_build_report_includes_acceptance_metrics():
    report = build_report(Path("tests/fixtures/passive_sample.md"))
    assert "passive_voice_ratio:" in report
    assert "modifier_budget_violations:" in report
    assert "parallel_structure_violations:" in report


def test_write_report_creates_file(tmp_path):
    out = tmp_path / "report.md"
    write_report(Path("tests/fixtures/hedged_sample.md"), out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Style Pass Report" in content


def test_compliant_sample_yields_zero_findings():
    report = build_report(Path("tests/fixtures/compliant_sample.md"))
    assert "Total findings:** 0" in report
    assert "hedge_count: 0" in report


def test_report_includes_new_elegance_metrics():
    report = build_report(Path("tests/fixtures/hedged_sample.md"))
    assert "listicle_abstract_count:" in report
    assert "rhythm_violations:" in report
