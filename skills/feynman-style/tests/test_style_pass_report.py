import pytest
pytestmark = pytest.mark.windows_canary

from scripts.style_pass_report import render_report


def test_report_includes_preservation_verdict():
    md = render_report(
        findings=[{"rule": "reading-grade", "line": 3, "grade": 14.2}],
        delta_score=1.8,
        preservation_ok=True,
    )
    assert "reading-grade" in md
    assert "PASS" in md  # preservation verdict surfaced

def test_report_flags_failed_preservation():
    md = render_report(findings=[], delta_score=1.0, preservation_ok=False)
    assert "FAIL" in md
