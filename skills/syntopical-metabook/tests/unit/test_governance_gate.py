"""governance_filter: pass rules meeting the schools-of-thought policy."""
from __future__ import annotations
from scripts.governance._stance import Stance
from scripts.governance._positions_io import Position
from scripts.governance.induction_gate import governance_filter, GateDecision


def _pos(rule, school, stance):
    return Position(
        rule_id=rule, rule_form="", source="induced",
        school=school, stance=stance,
        supporting_atoms=[], supporting_docs=[],
        contradicting_atoms=[], contradicting_docs=[],
        declared_by_charter=False, induction_prov="",
    )


def test_rule_with_two_supporters_no_contradictors_passes():
    positions = [
        _pos("r1", "praos", Stance.SUPPORTS),
        _pos("r1", "casper", Stance.SUPPORTS),
        _pos("r1", "algorand", Stance.SILENT),
    ]
    decisions = governance_filter(["r1"], positions, min_supports=2, max_contradictors=0)
    assert decisions["r1"] == GateDecision.PASS


def test_rule_with_contradictor_is_quarantined():
    positions = [
        _pos("r1", "praos", Stance.SUPPORTS),
        _pos("r1", "casper", Stance.SUPPORTS),
        _pos("r1", "algorand", Stance.CONTRADICTS),
    ]
    decisions = governance_filter(["r1"], positions, min_supports=2, max_contradictors=0)
    assert decisions["r1"] == GateDecision.QUARANTINE_CONTRADICTED


def test_rule_with_too_few_supporters_is_quarantined():
    positions = [
        _pos("r1", "praos", Stance.SUPPORTS),
    ]
    decisions = governance_filter(["r1"], positions, min_supports=2, max_contradictors=0)
    assert decisions["r1"] == GateDecision.QUARANTINE_INSUFFICIENT_SUPPORT


def test_missing_rule_is_unknown():
    positions = []
    decisions = governance_filter(["r-missing"], positions, min_supports=2, max_contradictors=0)
    assert decisions["r-missing"] == GateDecision.UNKNOWN
