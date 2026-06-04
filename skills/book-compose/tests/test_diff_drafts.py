import pytest

pytestmark = pytest.mark.windows_canary

from scripts.diff_drafts import diff_drafts


def test_diff_reports_added_section(tmp_path):
    a = tmp_path / "a.md"; a.write_text("# Title\n\n## A\n\nbody.\n", encoding="utf-8")
    b = tmp_path / "b.md"; b.write_text("# Title\n\n## A\n\nbody.\n\n## B\n\nnew.\n", encoding="utf-8")
    result = diff_drafts(a, b)
    assert "## B" in result["added_sections"]
    assert result["removed_sections"] == []


def test_diff_reports_removed_section(tmp_path):
    a = tmp_path / "a.md"; a.write_text("# T\n\n## A\n\nbody.\n\n## B\n\nbody.\n", encoding="utf-8")
    b = tmp_path / "b.md"; b.write_text("# T\n\n## A\n\nbody.\n", encoding="utf-8")
    result = diff_drafts(a, b)
    assert "## B" in result["removed_sections"]
    assert result["added_sections"] == []


def test_diff_word_delta(tmp_path):
    a = tmp_path / "a.md"; a.write_text("one two three", encoding="utf-8")
    b = tmp_path / "b.md"; b.write_text("one two three four five", encoding="utf-8")
    assert diff_drafts(a, b)["word_delta"] == 2
