"""dispatch_panel builds dispatch packets via book-review with optional few-shot context."""
import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "synthetic_outcomes" / "sample-pass-1"


def _make_workspace(tmp_path: Path, chapter_id: str = "ch-test") -> Path:
    """Create a minimal workspace with one draft chapter."""
    workspace = tmp_path / "workspace"
    drafts = workspace / "chapters" / "drafts" / chapter_id
    drafts.mkdir(parents=True)
    (drafts / "draft.md").write_text("# test chapter\n\nbody.\n", encoding="utf-8")
    contracts = workspace / "chapters" / "contracts"
    contracts.mkdir(parents=True)
    (contracts / f"{chapter_id}.yaml").write_text(
        "title: Test\npurpose: synthesis\naudience: testers\n",
        encoding="utf-8",
    )
    return workspace


def _panel(personas, exemplar_paths=None, per_persona=0):
    from scripts.load_panel import Panel, PersonaConfig, VerdictConfig, OutcomesConfig, OutputConfig
    return Panel(
        panel_id="t", artifact_scope="chapter", description="",
        personas=[PersonaConfig(id=p, severity_gate=g) for p, g in personas],
        verdict=VerdictConfig(hard_gate=False, soft_gate_rule="any_critical_from_gating"),
        outcomes=OutcomesConfig(
            exemplar_paths=exemplar_paths or [],
            per_persona_exemplars=per_persona,
        ),
        output=OutputConfig(panel_report_path="x.md", verdict_path="x.json"),
    )


def test_packets_built_for_each_persona(tmp_path):
    from scripts.dispatch_panel import build_packets
    panel = _panel([("gottlieb", "gating"), ("lay-reader", "advisory")])
    workspace = _make_workspace(tmp_path)
    packets = build_packets(workspace, "ch-test", panel)
    assert len(packets) == 2
    assert {p.persona_id for p in packets} == {"gottlieb", "lay-reader"}


def test_packets_include_few_shot_when_outcomes_configured(tmp_path):
    from scripts.dispatch_panel import build_packets
    panel = _panel(
        [("gottlieb", "gating")],
        exemplar_paths=[str(FIXTURES)],
        per_persona=1,
    )
    workspace = _make_workspace(tmp_path)
    packets = build_packets(workspace, "ch-test", panel, outcomes_seed=42)
    assert len(packets) == 1
    assert "Recent findings" in packets[0].prompt
    assert "synthetic gottlieb critical" in packets[0].prompt.lower()


def test_packets_skip_few_shot_when_per_persona_zero(tmp_path):
    from scripts.dispatch_panel import build_packets
    panel = _panel(
        [("gottlieb", "gating")],
        exemplar_paths=[str(FIXTURES)],
        per_persona=0,
    )
    workspace = _make_workspace(tmp_path)
    packets = build_packets(workspace, "ch-test", panel)
    assert "Recent findings" not in packets[0].prompt
