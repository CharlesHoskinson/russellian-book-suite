"""Positions ledger read/write — byte-deterministic EDN."""
from __future__ import annotations
from pathlib import Path
from scripts.governance._stance import Stance
from scripts.governance._positions_io import (
    Position, write_positions, read_positions,
)


def _pos(rule="r1", school="praos", stance=Stance.SUPPORTS):
    return Position(
        rule_id=rule,
        rule_form="(forall [(?e :execution)] ...)",
        source="induced",
        school=school,
        stance=stance,
        supporting_atoms=["a1", "a2"],
        supporting_docs=["praos2017"],
        contradicting_atoms=[],
        contradicting_docs=[],
        declared_by_charter=False,
        induction_prov="induced-theory.prov.edn#:r1",
    )


def test_write_then_read_round_trips(tmp_path):
    out = tmp_path / "positions.edn"
    write_positions(out, [_pos(), _pos(school="algorand", stance=Stance.CONTRADICTS)],
                    generated_at="2026-05-20T18:00:00Z")
    assert out.exists()
    rows = read_positions(out)
    assert len(rows) == 2
    assert rows[0].rule_id == "r1"
    assert rows[1].stance == Stance.CONTRADICTS


def test_write_is_byte_deterministic(tmp_path):
    out1 = tmp_path / "a.edn"
    out2 = tmp_path / "b.edn"
    rows = [_pos(school="b"), _pos(school="a"), _pos(school="c")]
    write_positions(out1, rows, generated_at="2026-05-20T18:00:00Z")
    write_positions(out2, rows, generated_at="2026-05-20T18:00:00Z")
    assert out1.read_bytes() == out2.read_bytes()


def test_write_sorts_positions_for_stability(tmp_path):
    """Same logical content in different order → same output bytes."""
    out1 = tmp_path / "x.edn"
    out2 = tmp_path / "y.edn"
    r1 = _pos(rule="r1", school="praos")
    r2 = _pos(rule="r2", school="algorand")
    write_positions(out1, [r1, r2], generated_at="2026-05-20T18:00:00Z")
    write_positions(out2, [r2, r1], generated_at="2026-05-20T18:00:00Z")
    assert out1.read_bytes() == out2.read_bytes()
