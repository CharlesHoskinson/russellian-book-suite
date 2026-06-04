"""Domain-neutral conformance canary — always runs (no external workspace).

Exercises both the induced-rule and defconstraint paths plus all renderers
against an in-repo workspace with curated schools.
"""
from __future__ import annotations
import shutil
from pathlib import Path
from scripts.governance.build_positions import build_positions
from scripts.governance.render_per_rule import render_per_rule
from scripts.governance.render_consensus_map import render_consensus_map
from scripts.governance.render_adversarial import render_adversarial
from scripts.governance._config import load_or_create_config
from scripts.governance._positions_io import read_positions
from scripts.governance._stance import Stance

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "workspaces" / "neutral-conformance"


def _ws(tmp_path):
    ws = tmp_path / "ws"
    shutil.copytree(FIXTURE, ws)
    return ws


def test_build_emits_both_sources(tmp_path):
    ws = _ws(tmp_path)
    build_positions(ws, generated_at="2026-05-31T00:00:00Z")
    rows = read_positions(ws / "syntopical" / "positions.edn")
    assert {r.source for r in rows} == {"induced", "defconstraint"}
    dc = {r.school: r for r in rows if r.rule_id == ":C001-method-x"}
    assert dc["school-a"].stance == Stance.SUPPORTS        # charter assert
    assert dc["school-a"].declared_by_charter is True


def test_charter_override_and_atom_inference(tmp_path):
    ws = _ws(tmp_path)
    build_positions(ws, generated_at="2026-05-31T00:00:00Z")
    rows = read_positions(ws / "syntopical" / "positions.edn")
    induced = {r.school: r for r in rows if r.rule_id == ":induced/r-001"}
    assert induced["school-a"].stance == Stance.SUPPORTS      # charter assert
    assert induced["school-b"].stance == Stance.CONTRADICTS   # charter reject
    assert induced["my-own-work"].stance == Stance.EXTENDS    # 1 member doc < supports_min_docs=2


def test_all_renderers_run(tmp_path):
    ws = _ws(tmp_path)
    build_positions(ws, generated_at="2026-05-31T00:00:00Z")
    pos = ws / "syntopical" / "positions.edn"
    assert render_per_rule(pos, ws / "syntopical" / "rules") >= 2
    render_consensus_map(pos, ws / "syntopical" / "figures")
    cfg = load_or_create_config(ws / "syntopical" / "governance-config.edn")
    render_adversarial(pos, ws / "syntopical" / "adversarial-review.md", cfg)
    assert (ws / "syntopical" / "figures" / "consensus-map.svg").exists()
    assert (ws / "syntopical" / "adversarial-review.md").exists()
