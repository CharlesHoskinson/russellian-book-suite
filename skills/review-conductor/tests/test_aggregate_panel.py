"""aggregate_panel emits verdict.json + panel-review.md and applies per-persona severity gates."""
import json
from pathlib import Path
from shutil import copytree

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "synthetic_reviews"


def _setup_workspace_with_reviews(tmp_path: Path, fixture_name: str, chapter_id: str = "ch-test") -> Path:
    workspace = tmp_path / "workspace"
    draft_dir = workspace / "chapters" / "drafts" / chapter_id
    draft_dir.mkdir(parents=True)
    (draft_dir / "draft.md").write_text("# test\n", encoding="utf-8")
    copytree(FIXTURES / fixture_name, draft_dir / "reviews")
    return workspace


def _panel(personas):
    from scripts.load_panel import Panel, PersonaConfig, VerdictConfig, OutcomesConfig, OutputConfig
    return Panel(
        panel_id="test", artifact_scope="chapter", description="",
        personas=[PersonaConfig(id=p, severity_gate=g) for p, g in personas],
        verdict=VerdictConfig(hard_gate=False, soft_gate_rule="any_critical_from_gating"),
        outcomes=OutcomesConfig(exemplar_paths=[], per_persona_exemplars=0),
        output=OutputConfig(
            panel_report_path="chapters/drafts/{chapter_id}/panel-review.md",
            verdict_path="chapters/drafts/{chapter_id}/verdict.json",
        ),
    )


def test_verdict_pass_when_all_clean(tmp_path):
    from scripts.aggregate_panel import run_aggregation
    workspace = _setup_workspace_with_reviews(tmp_path, "all-clean")
    panel = _panel([("gottlieb", "gating"), ("lay-reader", "advisory")])
    verdict = run_aggregation(workspace, "ch-test", panel)
    assert verdict["verdict"] == "pass"
    assert verdict["gating_criticals"] == 0
    assert verdict["advisory_criticals"] == 0


def test_verdict_soft_gate_fail_when_gating_critical(tmp_path):
    from scripts.aggregate_panel import run_aggregation
    workspace = _setup_workspace_with_reviews(tmp_path, "gating-critical")
    panel = _panel([("gottlieb", "gating"), ("lay-reader", "advisory")])
    verdict = run_aggregation(workspace, "ch-test", panel)
    assert verdict["verdict"] == "soft-gate-fail"
    assert verdict["gating_criticals"] == 1


def test_verdict_pass_when_only_advisory_critical(tmp_path):
    from scripts.aggregate_panel import run_aggregation
    workspace = _setup_workspace_with_reviews(tmp_path, "advisory-critical-only")
    panel = _panel([("gottlieb", "gating"), ("lay-reader", "advisory")])
    verdict = run_aggregation(workspace, "ch-test", panel)
    assert verdict["verdict"] == "pass"
    assert verdict["gating_criticals"] == 0
    assert verdict["advisory_criticals"] == 1


def test_verdict_json_written_to_workspace(tmp_path):
    from scripts.aggregate_panel import run_aggregation
    workspace = _setup_workspace_with_reviews(tmp_path, "gating-critical")
    panel = _panel([("gottlieb", "gating"), ("lay-reader", "advisory")])
    verdict = run_aggregation(workspace, "ch-test", panel)
    verdict_path = workspace / "chapters" / "drafts" / "ch-test" / "verdict.json"
    assert verdict_path.is_file()
    on_disk = json.loads(verdict_path.read_text(encoding="utf-8"))
    assert on_disk["verdict"] == verdict["verdict"]


def test_panel_review_md_written(tmp_path):
    from scripts.aggregate_panel import run_aggregation
    workspace = _setup_workspace_with_reviews(tmp_path, "gating-critical")
    panel = _panel([("gottlieb", "gating"), ("lay-reader", "advisory")])
    run_aggregation(workspace, "ch-test", panel)
    report = workspace / "chapters" / "drafts" / "ch-test" / "panel-review.md"
    assert report.is_file()
    text = report.read_text(encoding="utf-8")
    assert "synthetic gottlieb critical" in text.lower()
