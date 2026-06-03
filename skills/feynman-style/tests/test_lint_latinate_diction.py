import pytest
pytestmark = pytest.mark.windows_canary

from pathlib import Path
from scripts.lint_latinate_diction import lint_latinate_diction


def test_flags_latinate_with_suggestion(tmp_path):
    md = tmp_path / "latinate.md"
    md.write_text("We utilize the mechanism to facilitate the demonstration.\n", encoding="utf-8")
    findings = lint_latinate_diction(md)
    terms = {f["term"]: f["suggestion"] for f in findings}
    assert terms.get("utilize") == "use"
    assert terms.get("facilitate") == "help"
    assert all(f["rule"] == "latinate-diction" for f in findings)

def test_plain_prose_passes(tmp_path):
    md = tmp_path / "plain.md"
    md.write_text("We use the tool to help the demo.\n", encoding="utf-8")
    assert lint_latinate_diction(md) == []

def test_match_on_continuation_line_reports_correct_line_col(tmp_path):
    md = tmp_path / "multiline.md"
    # A single sentence wrapped across two physical lines; "utilize" sits on line 2.
    md.write_text(
        "We will do this and then\nutilize the mechanism here.\n",
        encoding="utf-8",
    )
    findings = lint_latinate_diction(md)
    util = next(f for f in findings if f["term"] == "utilize")
    assert util["line"] == 2
    assert util["col"] == 1
