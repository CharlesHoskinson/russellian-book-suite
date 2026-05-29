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


def test_dedup_keeps_distinct_substring_findings():
    from scripts.aggregate_reviews import _dedup_findings
    pairs = [
        ("alpha", "weak argument"),
        ("beta", "weak argument about the gold standard in ch.3"),
    ]
    out = _dedup_findings(pairs)
    texts = {d["text"] for d in out}
    assert "weak argument" in texts
    assert "weak argument about the gold standard in ch.3" in texts
    assert len(out) == 2


def test_dedup_merges_exact_duplicates_across_personas():
    from scripts.aggregate_reviews import _dedup_findings
    pairs = [
        ("alpha", "Listicle abstract on line 14."),
        ("beta", "listicle abstract on line 14."),
    ]
    out = _dedup_findings(pairs)
    assert len(out) == 1
    assert "alpha" in out[0]["persona"]
    assert "beta" in out[0]["persona"]


def test_severity_counts_sum_raw_per_persona_not_deduped(tmp_path):
    # Two personas raise the same critical finding; the gating count must
    # remain the raw per-persona sum (2), not collapse to the deduped 1.
    workspace = tmp_path / "book"
    reviews_dir = workspace / "chapters" / "drafts" / "ch-04" / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)
    (workspace / "CLAUDE.md").write_text("# marker\n", encoding="utf-8")
    body = (
        "## Critical findings (gating)\n- Same critical finding.\n\n"
        "## Important findings\n(none)\n\n## Minor findings\n(none)\n"
    )
    for pid in ("alpha", "beta"):
        (reviews_dir / f"{pid}.md").write_text(
            f"---\npersona: {pid}\nchapter_id: ch-04\nverdict: NEEDS_WORK\n"
            f"critical_count: 1\nimportant_count: 0\nminor_count: 0\n"
            f"reviewed_at: 2026-05-10T12:00:00+00:00\n---\n\n" + body,
            encoding="utf-8",
        )
    result = aggregate_reviews(workspace, "ch-04")
    assert result.severity_counts["critical"] == 2
    # display list still deduplicates to a single merged entry
    assert len(result.critical) == 1
    text = result.report_path.read_text(encoding="utf-8")
    assert "Critical: 2" in text


def test_aggregate_handles_no_reviews(tmp_path):
    workspace = tmp_path / "book"
    (workspace / "chapters" / "drafts" / "ch-04" / "reviews").mkdir(parents=True, exist_ok=True)
    (workspace / "CLAUDE.md").write_text("# marker\n", encoding="utf-8")
    result = aggregate_reviews(workspace, "ch-04")
    assert result.severity_counts == {"critical": 0, "important": 0, "minor": 0}
    assert result.per_persona_verdicts == {}
    assert result.report_path.exists()
