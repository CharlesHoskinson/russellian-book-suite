"""Renderers refuse a positions.edn older than its source ledgers."""
from __future__ import annotations
import os
import pytest
from scripts._staleness import StaleArtifactError
from scripts.governance._stance import Stance
from scripts.governance._positions_io import Position, write_positions
from scripts.governance.render_per_rule import render_per_rule


def _ws(tmp_path):
    ws = tmp_path / "ws"
    (ws / "syntopical").mkdir(parents=True)
    (ws / "knowledge" / "claims").mkdir(parents=True)
    return ws


def _pos():
    return Position(
        rule_id="r1", rule_form="", source="induced", school="school-a",
        stance=Stance.SUPPORTS, supporting_atoms=[], supporting_docs=[],
        contradicting_atoms=[], contradicting_docs=[],
        declared_by_charter=False, induction_prov="",
    )


def test_render_per_rule_refuses_stale(tmp_path):
    ws = _ws(tmp_path)
    positions = ws / "syntopical" / "positions.edn"
    write_positions(positions, [_pos()], generated_at="2026-05-31T00:00:00Z")
    ledger = ws / "knowledge" / "claims" / "ledger.jsonl"
    ledger.write_text("{}\n", encoding="utf-8")
    os.utime(positions, (1000, 1000))
    os.utime(ledger, (2000, 2000))
    with pytest.raises(StaleArtifactError):
        render_per_rule(positions, ws / "syntopical" / "rules")


def test_render_per_rule_runs_when_fresh(tmp_path):
    ws = _ws(tmp_path)
    positions = ws / "syntopical" / "positions.edn"
    write_positions(positions, [_pos()], generated_at="2026-05-31T00:00:00Z")
    ledger = ws / "knowledge" / "claims" / "ledger.jsonl"
    ledger.write_text("{}\n", encoding="utf-8")
    os.utime(ledger, (1000, 1000))
    os.utime(positions, (2000, 2000))
    n = render_per_rule(positions, ws / "syntopical" / "rules")
    assert n == 1
