from pathlib import Path

from scripts.chapter_contract_check import check_draft, _compute_metrics


CONTRACT = {
    "chapter_id": "ch-01", "title": "Sample",
    "purpose": "purpose long enough to satisfy schema",
    "audience": "senior-engineer", "chapter_type": "reference",
    "evidence_requirements": {"minimum_verified_claims": 0, "max_unresolved_conflicts": 0},
    "acceptance_tests": [
        "persona_critical_count == 0",
        "persona_reviews_complete == True",
    ],
    "output_formats": ["markdown"],
}


def _make_workspace_with_draft(tmp_path: Path) -> Path:
    ws = tmp_path / "book"
    ch = ws / "chapters" / "drafts" / "ch-01"
    ch.mkdir(parents=True, exist_ok=True)
    (ws / "CLAUDE.md").write_text("# marker\n", encoding="utf-8")
    (ch / "draft.md").write_text("# Sample\n\nBody.\n", encoding="utf-8")
    return ws


def test_no_persona_review_fails_complete_check(tmp_path):
    ws = _make_workspace_with_draft(tmp_path)
    metrics = _compute_metrics(ws / "chapters" / "drafts" / "ch-01" / "draft.md")
    assert metrics["persona_reviews_complete"] is False
    assert metrics["persona_critical_count"] == 0


def test_persona_review_with_zero_critical_passes(tmp_path):
    ws = _make_workspace_with_draft(tmp_path)
    review_path = ws / "chapters" / "drafts" / "ch-01" / "persona-review.md"
    review_path.write_text(
        "# Persona Review\n\n"
        "## Severity counts\n\n"
        "- Critical: 0\n"
        "- Important: 3\n"
        "- Minor: 5\n",
        encoding="utf-8",
    )
    import time
    time.sleep(0.05)
    review_path.touch()
    metrics = _compute_metrics(ws / "chapters" / "drafts" / "ch-01" / "draft.md")
    assert metrics["persona_reviews_complete"] is True
    assert metrics["persona_critical_count"] == 0


def test_persona_review_with_critical_findings_metric_reflects_count(tmp_path):
    ws = _make_workspace_with_draft(tmp_path)
    review_path = ws / "chapters" / "drafts" / "ch-01" / "persona-review.md"
    review_path.write_text(
        "# Persona Review\n\n"
        "## Severity counts\n\n"
        "- Critical: 3\n"
        "- Important: 7\n"
        "- Minor: 12\n",
        encoding="utf-8",
    )
    import time
    time.sleep(0.05)
    review_path.touch()
    metrics = _compute_metrics(ws / "chapters" / "drafts" / "ch-01" / "draft.md")
    assert metrics["persona_critical_count"] == 3


def test_check_draft_fails_when_critical_count_nonzero(tmp_path):
    ws = _make_workspace_with_draft(tmp_path)
    review_path = ws / "chapters" / "drafts" / "ch-01" / "persona-review.md"
    review_path.write_text(
        "# Persona Review\n\n## Severity counts\n\n- Critical: 2\n- Important: 0\n- Minor: 0\n",
        encoding="utf-8",
    )
    import time
    time.sleep(0.05)
    review_path.touch()
    result = check_draft(ws / "chapters" / "drafts" / "ch-01" / "draft.md", CONTRACT)
    assert result.passes is False
    assert any("persona_critical_count" in t for t in result.failed_tests)
