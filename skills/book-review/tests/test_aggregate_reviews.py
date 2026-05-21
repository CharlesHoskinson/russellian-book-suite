import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path
import shutil
from scripts.aggregate_reviews import aggregate_reviews, AggregatedReview


def _seed_workspace_with_reviews(tmp_path: Path, fixture_dir: Path) -> Path:
    workspace = tmp_path / "book"
    reviews_dir = workspace / "chapters" / "drafts" / "ch-04" / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)
    (workspace / "CLAUDE.md").write_text("# workspace marker\n", encoding="utf-8")
    for src in fixture_dir.glob("*.md"):
        shutil.copy(src, reviews_dir / src.name)
    return workspace


def test_aggregate_collects_severity_counts(tmp_path):
    fixtures = Path("tests/fixtures/synthetic_reviews")
    workspace = _seed_workspace_with_reviews(tmp_path, fixtures)
    result = aggregate_reviews(workspace, "ch-04")
    assert isinstance(result, AggregatedReview)
    assert result.severity_counts["critical"] == 2
    assert result.severity_counts["important"] == 5
    assert result.severity_counts["minor"] == 6


def test_aggregate_records_per_persona_verdicts(tmp_path):
    fixtures = Path("tests/fixtures/synthetic_reviews")
    workspace = _seed_workspace_with_reviews(tmp_path, fixtures)
    result = aggregate_reviews(workspace, "ch-04")
    assert result.per_persona_verdicts["gottlieb"] == "NEEDS_WORK"
    assert result.per_persona_verdicts["lay-reader"] == "APPROVED_WITH_NOTES"


def test_aggregate_writes_persona_review_md(tmp_path):
    fixtures = Path("tests/fixtures/synthetic_reviews")
    workspace = _seed_workspace_with_reviews(tmp_path, fixtures)
    result = aggregate_reviews(workspace, "ch-04")
    assert result.report_path.exists()
    text = result.report_path.read_text(encoding="utf-8")
    assert "Critical: 2" in text
    assert "gottlieb" in text
    assert "lay-reader" in text


def test_aggregate_handles_no_reviews(tmp_path):
    workspace = tmp_path / "book"
    (workspace / "chapters" / "drafts" / "ch-04" / "reviews").mkdir(parents=True, exist_ok=True)
    (workspace / "CLAUDE.md").write_text("# marker\n", encoding="utf-8")
    result = aggregate_reviews(workspace, "ch-04")
    assert result.severity_counts == {"critical": 0, "important": 0, "minor": 0}
    assert result.per_persona_verdicts == {}
    assert result.report_path.exists()
