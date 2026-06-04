"""End-to-end conductor: build packets, run stubbed dispatcher writes synthetic reviews, aggregate."""
import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "synthetic_reviews"


def _stub_dispatcher(reviews_src: Path):
    """Returns a dispatcher callable that copies pre-canned per-persona review markdown
    into the packet's output_path. Simulates a subagent writing its review."""
    def dispatcher(packet):
        src = reviews_src / f"{packet.persona_id}.md"
        if src.is_file():
            packet.output_path.parent.mkdir(parents=True, exist_ok=True)
            packet.output_path.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return dispatcher


def _make_workspace(tmp_path: Path, chapter_id: str = "ch-test") -> Path:
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


def test_run_panel_pass_verdict(tmp_path):
    from scripts.conductor import run_panel
    panel_yaml = Path(__file__).resolve().parent / "fixtures" / "panel-default.yaml"
    workspace = _make_workspace(tmp_path)
    verdict = run_panel(
        workspace=workspace,
        chapter_id="ch-test",
        panel_path=panel_yaml,
        dispatcher=_stub_dispatcher(FIXTURES / "all-clean"),
    )
    assert verdict["verdict"] == "pass"


def test_run_panel_soft_gate_fail(tmp_path):
    from scripts.conductor import run_panel
    panel_yaml = Path(__file__).resolve().parent / "fixtures" / "panel-default.yaml"
    workspace = _make_workspace(tmp_path)
    verdict = run_panel(
        workspace=workspace,
        chapter_id="ch-test",
        panel_path=panel_yaml,
        dispatcher=_stub_dispatcher(FIXTURES / "gating-critical"),
    )
    assert verdict["verdict"] == "soft-gate-fail"
    assert verdict["gating_criticals"] >= 1
