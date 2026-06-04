"""Adversarial review: flags contradictions against self-school positions."""
from __future__ import annotations
from pathlib import Path
from scripts.governance._stance import Stance
from scripts.governance._positions_io import Position, write_positions
from scripts.governance._config import GovernanceConfig, DEFAULTS
from scripts.governance.render_adversarial import render_adversarial


def _pos(rule, school, stance, **kw):
    return Position(
        rule_id=rule, rule_form=kw.get("form", ""),
        source="induced", school=school, stance=stance,
        supporting_atoms=[], supporting_docs=[],
        contradicting_atoms=[], contradicting_docs=[],
        declared_by_charter=False, induction_prov="",
    )


def test_flags_contradiction_from_other_school(tmp_path):
    pos = tmp_path / "positions.edn"
    write_positions(pos, [
        _pos("r1", "my-own-work", Stance.SUPPORTS),
        _pos("r1", "algorand", Stance.CONTRADICTS),
    ], generated_at="2026-05-20T18:00:00Z")
    cfg = GovernanceConfig(**DEFAULTS)
    out = tmp_path / "adversarial-review.md"
    render_adversarial(pos, out, cfg)
    text = out.read_text(encoding="utf-8")
    assert "r1" in text
    assert "algorand" in text
    assert "contradicts" in text.lower()


def test_omits_silent_schools(tmp_path):
    pos = tmp_path / "positions.edn"
    write_positions(pos, [
        _pos("r1", "my-own-work", Stance.SUPPORTS),
        _pos("r1", "casper", Stance.SILENT),
    ], generated_at="2026-05-20T18:00:00Z")
    cfg = GovernanceConfig(**DEFAULTS)
    out = tmp_path / "adv.md"
    render_adversarial(pos, out, cfg)
    text = out.read_text(encoding="utf-8")
    assert "casper" not in text or "(no conflicts" in text  # silent schools are not flagged


def test_skips_rules_self_school_does_not_support(tmp_path):
    pos = tmp_path / "positions.edn"
    write_positions(pos, [
        _pos("r1", "my-own-work", Stance.SILENT),       # not the author's position
        _pos("r1", "algorand", Stance.CONTRADICTS),
    ], generated_at="2026-05-20T18:00:00Z")
    cfg = GovernanceConfig(**DEFAULTS)
    out = tmp_path / "adv.md"
    render_adversarial(pos, out, cfg)
    text = out.read_text(encoding="utf-8")
    assert "r1" not in text or "no contested positions" in text.lower()
