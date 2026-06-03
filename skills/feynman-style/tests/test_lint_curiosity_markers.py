import pytest
pytestmark = pytest.mark.windows_canary

from pathlib import Path
from scripts.lint_curiosity_markers import lint_curiosity_markers, count_markers


def test_counts_curiosity_phrases():
    text = "The funny thing is, nobody really knows why. Here's the puzzle that bugged everyone."
    assert count_markers(text) >= 2

def test_flags_passage_without_curiosity(tmp_path):
    md = tmp_path / "flat.md"
    md.write_text(
        "The procedure runs in three stages. Each stage validates its input. "
        "The final stage emits the result. The result is stored in the ledger. "
        "Downstream consumers read the ledger entry directly.\n",
        encoding="utf-8",
    )
    findings = lint_curiosity_markers(md)
    assert any(f["rule"] == "curiosity-absent" for f in findings)
