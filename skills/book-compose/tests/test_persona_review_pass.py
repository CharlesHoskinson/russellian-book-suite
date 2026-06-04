import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path
import yaml

from scripts.persona_review_pass import prepare_packets, aggregate


def _seed(tmp_path: Path) -> Path:
    workspace = tmp_path / "book"
    chapter_dir = workspace / "chapters" / "drafts" / "ch-01"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (workspace / "CLAUDE.md").write_text("# marker\n", encoding="utf-8")
    (chapter_dir / "draft.md").write_text("# Sample\n\nFirst paragraph.\n", encoding="utf-8")

    contracts = workspace / "chapters" / "contracts"
    contracts.mkdir(parents=True, exist_ok=True)
    (contracts / "ch-01.yaml").write_text(yaml.safe_dump({
        "chapter_id": "ch-01", "title": "Sample",
        "purpose": "purpose long enough to satisfy schema",
        "audience": "senior-engineer", "chapter_type": "reference",
        "evidence_requirements": {"minimum_verified_claims": 0, "max_unresolved_conflicts": 0},
        "acceptance_tests": ["hedge_count == 0"],
        "output_formats": ["markdown"],
    }), encoding="utf-8")
    return workspace


def test_prepare_packets_returns_seven(tmp_path):
    """After PR-A added ai-slop-detector + first-time-visitor, book-review ships 7 personas."""
    workspace = _seed(tmp_path)
    packets = prepare_packets(workspace, "ch-01")
    assert len(packets) == 7


def test_aggregate_returns_aggregated_review(tmp_path):
    workspace = _seed(tmp_path)
    result = aggregate(workspace, "ch-01")
    assert result.severity_counts["critical"] == 0


def test_run_panel_returns_verdict_dict(tmp_path):
    """run_panel delegates to review-conductor and returns a verdict dict."""
    from scripts.persona_review_pass import run_panel
    workspace = _seed(tmp_path)

    # No dispatcher: no reviews are written. The chapter-default panel has
    # gating personas (gottlieb, domain-expert, copyeditor, ai-slop-detector);
    # with zero reports they are all "missing gating reports", so the conductor's
    # fail-closed completeness check returns "hard-gate-fail" rather than scoring
    # the absent personas as zero criticals. (An empty panel does not pass — see
    # review-conductor's test_missing_gating_report_fails_closed.)
    verdict = run_panel(workspace, "ch-01", panel_id="chapter-default", dispatcher=None)
    assert verdict["panel_id"] == "chapter-default"
    assert verdict["artifact"] == {"type": "chapter", "id": "ch-01"}
    assert verdict["verdict"] == "hard-gate-fail"
    assert verdict["gating_criticals"] == 0


def test_load_system_prompt_returns_text_for_known_mode():
    from scripts.persona_review_pass import load_system_prompt
    text = load_system_prompt("technical-exposition")
    assert "Role" in text or "role" in text


def test_load_system_prompt_falls_back_for_unknown_mode():
    from scripts.persona_review_pass import load_system_prompt
    text = load_system_prompt("nonexistent-mode")
    assert text  # falls back to default; non-empty
