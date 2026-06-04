"""Consensus map: bipartite schools×rules with stance-coloured edges."""
from __future__ import annotations
from pathlib import Path
from scripts.governance._stance import Stance
from scripts.governance._positions_io import Position, write_positions
from scripts.governance.render_consensus_map import render_consensus_map


def _pos(rule, school, stance):
    return Position(
        rule_id=rule, rule_form="", source="induced",
        school=school, stance=stance,
        supporting_atoms=[], supporting_docs=[],
        contradicting_atoms=[], contradicting_docs=[],
        declared_by_charter=False, induction_prov="",
    )


def test_emits_tex_and_svg(tmp_path):
    pos = tmp_path / "positions.edn"
    write_positions(pos, [
        _pos("r1", "praos", Stance.SUPPORTS),
        _pos("r1", "algorand", Stance.CONTRADICTS),
        _pos("r2", "praos", Stance.SILENT),
    ], generated_at="2026-05-20T18:00:00Z")

    out_dir = tmp_path / "figures"
    render_consensus_map(pos, out_dir)
    assert (out_dir / "consensus-map.tex").exists()
    assert (out_dir / "consensus-map.svg").exists()


def test_tex_contains_one_node_per_school_and_rule(tmp_path):
    pos = tmp_path / "positions.edn"
    write_positions(pos, [
        _pos("r1", "praos", Stance.SUPPORTS),
        _pos("r1", "algorand", Stance.CONTRADICTS),
    ], generated_at="2026-05-20T18:00:00Z")
    out_dir = tmp_path / "figures"
    render_consensus_map(pos, out_dir)
    tex = (out_dir / "consensus-map.tex").read_text(encoding="utf-8")
    assert "praos" in tex
    assert "algorand" in tex
    assert "r1" in tex


def test_byte_deterministic(tmp_path):
    pos = tmp_path / "positions.edn"
    write_positions(pos, [
        _pos("r1", "praos", Stance.SUPPORTS),
    ], generated_at="2026-05-20T18:00:00Z")
    o1 = tmp_path / "o1"
    o2 = tmp_path / "o2"
    render_consensus_map(pos, o1)
    render_consensus_map(pos, o2)
    assert (o1 / "consensus-map.tex").read_bytes() == (o2 / "consensus-map.tex").read_bytes()
    assert (o1 / "consensus-map.svg").read_bytes() == (o2 / "consensus-map.svg").read_bytes()
