"""Smoke test: the seed outcomes exemplar parses through the existing review-report parser."""
from pathlib import Path

from scripts.dispatch_review import parse_review_report

OUTCOMES_DIR = (
    Path(__file__).resolve().parent.parent
    / "references" / "outcomes" / "readme-pass-2026-05-13"
)


def test_outcomes_seed_directory_exists():
    assert OUTCOMES_DIR.is_dir()
    assert (OUTCOMES_DIR / "README.md").is_file()
    assert (OUTCOMES_DIR / "curation-notes.md").is_file()


def test_outcomes_seed_has_one_file_per_persona():
    expected = {
        "ai-slop-detector", "copyeditor", "domain-expert",
        "enjoyment-reader", "first-time-visitor",
        "gottlieb", "lay-reader",
    }
    found = {p.stem for p in OUTCOMES_DIR.glob("*.md")} - {"README", "curation-notes"}
    assert found == expected


def test_outcomes_seed_files_parse_as_review_reports():
    for persona_id in [
        "ai-slop-detector", "copyeditor", "domain-expert",
        "enjoyment-reader", "first-time-visitor",
        "gottlieb", "lay-reader",
    ]:
        path = OUTCOMES_DIR / f"{persona_id}.md"
        result = parse_review_report(path)
        assert result.persona_id == persona_id
        assert result.critical or result.important or result.minor, (
            f"{persona_id} exemplar has no findings"
        )
