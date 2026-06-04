"""Per-rule report renderer."""
from __future__ import annotations
from pathlib import Path
from scripts.governance._stance import Stance
from scripts.governance._positions_io import Position, write_positions
from scripts.governance.render_per_rule import render_per_rule


def _pos(rule, school, stance, **kw):
    return Position(
        rule_id=rule,
        rule_form=kw.get("form", "(forall [(?e :execution)] ...)"),
        source=kw.get("source", "induced"),
        school=school,
        stance=stance,
        supporting_atoms=kw.get("sup_atoms", []),
        supporting_docs=kw.get("sup_docs", []),
        contradicting_atoms=kw.get("con_atoms", []),
        contradicting_docs=kw.get("con_docs", []),
        declared_by_charter=kw.get("declared", False),
        induction_prov=kw.get("induction_prov", ""),
    )


def test_render_per_rule_emits_one_file_per_rule(tmp_path):
    positions = tmp_path / "positions.edn"
    write_positions(positions, [
        _pos("r1", "praos", Stance.SUPPORTS),
        _pos("r1", "algorand", Stance.CONTRADICTS),
        _pos("r2", "praos", Stance.SILENT),
    ], generated_at="2026-05-20T18:00:00Z")

    out_dir = tmp_path / "syntopical" / "rules"
    render_per_rule(positions, out_dir)

    assert (out_dir / "r1.md").exists()
    assert (out_dir / "r2.md").exists()


def test_render_per_rule_table_lists_each_school(tmp_path):
    positions = tmp_path / "positions.edn"
    write_positions(positions, [
        _pos("r1", "praos", Stance.SUPPORTS, sup_docs=["praos2017"]),
        _pos("r1", "algorand", Stance.CONTRADICTS, declared=True),
    ], generated_at="2026-05-20T18:00:00Z")
    out_dir = tmp_path / "syntopical" / "rules"
    render_per_rule(positions, out_dir)

    text = (out_dir / "r1.md").read_text(encoding="utf-8")
    assert "| praos | supports" in text
    assert "| algorand | contradicts" in text
    assert "praos2017" in text


def test_render_per_rule_is_byte_deterministic(tmp_path):
    positions = tmp_path / "positions.edn"
    write_positions(positions, [
        _pos("r1", "praos", Stance.SUPPORTS),
    ], generated_at="2026-05-20T18:00:00Z")

    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    render_per_rule(positions, out1)
    render_per_rule(positions, out2)
    assert (out1 / "r1.md").read_bytes() == (out2 / "r1.md").read_bytes()
