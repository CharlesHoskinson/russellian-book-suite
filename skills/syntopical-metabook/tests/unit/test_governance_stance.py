"""Stance-derivation tests: charter override + atom-inferred + edge cases."""
from __future__ import annotations
import pytest
from scripts.governance._schools import School
from scripts.governance._config import GovernanceConfig, DEFAULTS
from scripts.governance._stance import (
    derive_stance, Stance, RuleEvidence,
)


def _cfg(**overrides):
    base = dict(DEFAULTS)
    base.update(overrides)
    return GovernanceConfig(**base)


def _school(slug, members=None, asserts=None, rejects=None):
    return School(
        slug=slug, name=slug, charter="-",
        members=members or [],
        canonical_asserts=asserts or [],
        canonical_rejects=rejects or [],
    )


def test_charter_assert_overrides_atoms():
    school = _school("praos", asserts=[":tau-leq-one"])
    evidence = RuleEvidence(
        rule_id=":tau-leq-one",
        supporting_docs=[],
        contradicting_docs=["algorand2017"],
        supporting_atoms=[],
        contradicting_atoms=[],
    )
    s = derive_stance(school, evidence, _cfg())
    assert s == Stance.SUPPORTS


def test_charter_reject_overrides_atoms():
    school = _school("praos", rejects=[":tau-multi-leader"])
    evidence = RuleEvidence(
        rule_id=":tau-multi-leader",
        supporting_docs=["praos2017"],
        contradicting_docs=[],
        supporting_atoms=[], contradicting_atoms=[],
    )
    s = derive_stance(school, evidence, _cfg())
    assert s == Stance.CONTRADICTS


def test_atom_inferred_supports_with_two_docs():
    school = _school("praos", members=["praos2017", "genesis2018"])
    evidence = RuleEvidence(
        rule_id=":r1",
        supporting_docs=["praos2017", "genesis2018"],
        contradicting_docs=[],
        supporting_atoms=["a1", "a2"], contradicting_atoms=[],
    )
    s = derive_stance(school, evidence, _cfg(supports_min_docs=2))
    assert s == Stance.SUPPORTS


def test_atom_inferred_contradicts_with_one_doc():
    school = _school("algorand", members=["algorand2017"])
    evidence = RuleEvidence(
        rule_id=":r1",
        supporting_docs=[],
        contradicting_docs=["algorand2017"],
        supporting_atoms=[], contradicting_atoms=["a3"],
    )
    s = derive_stance(school, evidence, _cfg())
    assert s == Stance.CONTRADICTS


def test_silent_when_no_intersection():
    school = _school("casper", members=["casperffg2017"])
    evidence = RuleEvidence(
        rule_id=":r1",
        supporting_docs=["praos2017"],
        contradicting_docs=[],
        supporting_atoms=["a1"], contradicting_atoms=[],
    )
    s = derive_stance(school, evidence, _cfg())
    assert s == Stance.SILENT


def test_extends_when_some_support_but_below_threshold():
    school = _school("praos", members=["praos2017", "genesis2018"])
    evidence = RuleEvidence(
        rule_id=":r1",
        supporting_docs=["praos2017"],          # 1 of 2 members
        contradicting_docs=[],
        supporting_atoms=["a1"], contradicting_atoms=[],
    )
    s = derive_stance(school, evidence, _cfg(supports_min_docs=2))
    assert s == Stance.EXTENDS


def test_silent_when_school_has_empty_members_and_no_charter_hit():
    school = _school("empty")
    evidence = RuleEvidence(
        rule_id=":r1",
        supporting_docs=["x"], contradicting_docs=[],
        supporting_atoms=[], contradicting_atoms=[],
    )
    s = derive_stance(school, evidence, _cfg())
    assert s == Stance.SILENT
