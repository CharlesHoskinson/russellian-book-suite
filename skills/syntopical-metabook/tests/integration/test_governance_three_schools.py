"""End-to-end against the three-schools fixture workspace."""
from __future__ import annotations
from pathlib import Path
import pytest
from scripts.governance._positions_io import read_positions
from scripts.governance._stance import Stance
from scripts.governance.build_positions import build_positions

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "workspaces" / "three-schools"


def test_build_positions_produces_one_row_per_rule_school(tmp_path):
    workspace = tmp_path / "ws"
    import shutil
    shutil.copytree(FIXTURE, workspace)

    build_positions(workspace, generated_at="2026-05-20T18:00:00Z")

    positions_path = workspace / "syntopical" / "positions.edn"
    assert positions_path.exists()
    rows = read_positions(positions_path)

    # 1 rule × 3 schools = 3 rows
    assert len(rows) == 3
    by_school = {r.school: r for r in rows}
    assert set(by_school) == {"school-a", "school-b", "my-own-work"}


def test_charter_override_wins_for_school_b(tmp_path):
    workspace = tmp_path / "ws"
    import shutil
    shutil.copytree(FIXTURE, workspace)
    build_positions(workspace, generated_at="2026-05-20T18:00:00Z")

    rows = read_positions(workspace / "syntopical" / "positions.edn")
    school_b_row = next(r for r in rows if r.school == "school-b")
    assert school_b_row.stance == Stance.CONTRADICTS
    assert school_b_row.declared_by_charter is False


def test_atom_inferred_supports_for_school_a(tmp_path):
    workspace = tmp_path / "ws"
    import shutil
    shutil.copytree(FIXTURE, workspace)
    build_positions(workspace, generated_at="2026-05-20T18:00:00Z")

    rows = read_positions(workspace / "syntopical" / "positions.edn")
    school_a_row = next(r for r in rows if r.school == "school-a")
    # school-a has charter assert too, but evidence covers both branches
    assert school_a_row.stance == Stance.SUPPORTS


def test_build_positions_is_idempotent(tmp_path):
    workspace = tmp_path / "ws"
    import shutil
    shutil.copytree(FIXTURE, workspace)
    build_positions(workspace, generated_at="2026-05-20T18:00:00Z")
    first = (workspace / "syntopical" / "positions.edn").read_bytes()
    build_positions(workspace, generated_at="2026-05-20T18:00:00Z")
    second = (workspace / "syntopical" / "positions.edn").read_bytes()
    assert first == second
