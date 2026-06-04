import pytest
pytestmark = pytest.mark.windows_canary

from pathlib import Path
from scripts.lint_conversational import lint_conversational


def test_flags_cold_formal_paragraph(tmp_path):
    md = tmp_path / "cold.md"
    md.write_text(
        "The system processes the input. The output is then produced. "
        "The transformation is deterministic. The result is recorded for later analysis. "
        "Subsequent stages consume the recorded result.\n",
        encoding="utf-8",
    )
    findings = lint_conversational(md, min_per_paragraph=1)
    assert findings
    assert findings[0]["rule"] == "conversational-cold"

def test_warm_paragraph_passes(tmp_path):
    md = tmp_path / "warm.md"
    md.write_text(
        "Now you might ask: what's really going on here? Well, it's simpler than you'd think. "
        "We just feed it the input, and out comes the answer.\n",
        encoding="utf-8",
    )
    assert lint_conversational(md, min_per_paragraph=1) == []
