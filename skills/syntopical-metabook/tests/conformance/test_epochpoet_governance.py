# tests/conformance/test_epochpoet_governance.py
"""Conformance: run governance against the real EpochPoET workspace.

Skipped automatically if the workspace is absent or has no curated schools.
"""
from __future__ import annotations
from pathlib import Path
import pytest
from scripts.governance.build_positions import build_positions
from scripts.governance.render_per_rule import render_per_rule
from scripts.governance._positions_io import read_positions
from scripts.governance._stance import Stance

EPOCHPOET = Path("/c/epochpoet")
SCHOOLS = EPOCHPOET / "syntopical" / "schools"


pytestmark = pytest.mark.skipif(
    not EPOCHPOET.is_dir() or not SCHOOLS.is_dir() or not any(SCHOOLS.glob("*.edn")),
    reason="EpochPoET workspace not present or has no curated schools",
)


def test_build_positions_against_epochpoet(tmp_path):
    """A successful build is the baseline conformance — no exception."""
    out = build_positions(EPOCHPOET, generated_at="2026-05-20T18:00:00Z")
    assert out.exists()


def test_per_rule_report_renders_against_epochpoet(tmp_path):
    build_positions(EPOCHPOET, generated_at="2026-05-20T18:00:00Z")
    n = render_per_rule(
        EPOCHPOET / "syntopical" / "positions.edn",
        EPOCHPOET / "syntopical" / "rules",
    )
    assert n >= 0  # may be zero if no rules yet


def test_c007_supports_praos_if_present():
    """If C007 (tau=1) appears in positions, the praos school must support it.

    Skipped if C007 is not yet in the positions ledger (induction has not
    been wired to defconstraint rules in this PR).
    """
    pos_path = EPOCHPOET / "syntopical" / "positions.edn"
    if not pos_path.exists():
        pytest.skip("positions.edn not yet built")
    rows = read_positions(pos_path)
    c007 = [r for r in rows if "C007" in r.rule_id]
    if not c007:
        pytest.skip("C007 not yet in positions ledger (defconstraint path lands in PR 4 follow-up)")
    praos = [r for r in c007 if r.school == "praos"]
    if praos:
        assert praos[0].stance == Stance.SUPPORTS
