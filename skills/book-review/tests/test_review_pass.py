import pytest

pytestmark = pytest.mark.windows_canary

from datetime import datetime, timezone
from pathlib import Path
import yaml

from scripts.review_pass import prepare_dispatch_packets, run_review_pass, DispatchPacket


def _seed_workspace(tmp_path: Path) -> Path:
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


def _stub_persona(persona_id: str, persona_dir: Path):
    persona_dir.mkdir(parents=True, exist_ok=True)
    (persona_dir / f"{persona_id}.md").write_text(
        f"---\npersona_id: {persona_id}\ndisplay_name: {persona_id.title()}\nrole: tester\n---\n\n"
        f"## Lens\nTest lens.\n\n## Severity rubric\nFlag bad things.\n",
        encoding="utf-8",
    )


def test_prepare_dispatch_packets_one_per_persona(tmp_path, monkeypatch):
    workspace = _seed_workspace(tmp_path)
    persona_dir = tmp_path / "personas"
    for pid in ("gottlieb", "lay-reader", "domain-expert", "copyeditor", "enjoyment-reader"):
        _stub_persona(pid, persona_dir)
    monkeypatch.setattr("scripts.persona_loader.PERSONAS_DIR", persona_dir)
    packets = prepare_dispatch_packets(workspace, "ch-01")
    persona_ids = {p.persona_id for p in packets}
    assert persona_ids == {"gottlieb", "lay-reader", "domain-expert", "copyeditor", "enjoyment-reader"}
    for p in packets:
        assert "Sample" in p.prompt or "First paragraph" in p.prompt
        assert p.output_path.parent.name == "reviews"


def test_prepare_dispatch_packets_subset(tmp_path, monkeypatch):
    workspace = _seed_workspace(tmp_path)
    persona_dir = tmp_path / "personas"
    _stub_persona("gottlieb", persona_dir)
    monkeypatch.setattr("scripts.persona_loader.PERSONAS_DIR", persona_dir)
    packets = prepare_dispatch_packets(workspace, "ch-01", personas=["gottlieb"])
    assert len(packets) == 1
    assert packets[0].persona_id == "gottlieb"


def _fake_dispatcher(packet: DispatchPacket) -> None:
    packet.output_path.parent.mkdir(parents=True, exist_ok=True)
    review = (
        f"---\n"
        f"persona: {packet.persona_id}\n"
        f"chapter_id: ch-01\n"
        f"verdict: APPROVED\n"
        f"critical_count: 0\n"
        f"important_count: 0\n"
        f"minor_count: 0\n"
        f"reviewed_at: {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n"
        f"---\n\n"
        f"## Verdict\nAPPROVED\n\n"
        f"## Critical findings (gating)\n(none)\n\n"
        f"## Important findings\n(none)\n\n"
        f"## Minor findings\n(none)\n\n"
        f"## Notes on voice and cadence\nClean.\n"
    )
    packet.output_path.write_text(review, encoding="utf-8")


def test_run_review_pass_with_injected_dispatcher(tmp_path, monkeypatch):
    workspace = _seed_workspace(tmp_path)
    persona_dir = tmp_path / "personas"
    for pid in ("gottlieb", "lay-reader", "domain-expert", "copyeditor", "enjoyment-reader"):
        _stub_persona(pid, persona_dir)
    monkeypatch.setattr("scripts.persona_loader.PERSONAS_DIR", persona_dir)
    aggregated = run_review_pass(workspace, "ch-01", dispatcher=_fake_dispatcher)
    assert aggregated.severity_counts["critical"] == 0
    assert aggregated.report_path.exists()
    assert len(aggregated.per_persona_verdicts) == 5
