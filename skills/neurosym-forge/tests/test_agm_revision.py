"""Tests for AGM-compliant theory revision (Phase Z, Tier 6).

Covers REQ-REVISE-040..046.

The test fixture sidecar uses the Phase Y ``ProvenanceSidecar`` if it is
present; otherwise the conditional fallback inside
``scripts._agm_revision`` exposes a minimal stub with the same surface.
Both code paths share these tests.
"""
from __future__ import annotations

import logging
from pathlib import Path

from scripts._agm_revision import (
    DOC_SATURATION,
    STATUS_ACTIVE,
    STATUS_QUARANTINED,
    STATUS_TENTATIVE,
    THRESHOLD_ACTIVE,
    THRESHOLD_TENTATIVE,
    ProvenanceSidecar,
    RevisionReport,
    revise_theory,
)


# ---------------------------------------------------------------------------
# Local helper — prov-dict builder with tier-6 schema defaults
# ---------------------------------------------------------------------------


def _prov(**overrides) -> dict:
    """Build a prov dict satisfying the full tier-6 schema.

    Callers pass only the fields the test cares about; the helper fills in
    safe defaults for the other required keys. Schema is closed (see
    `scripts/_provenance.py::_REQUIRED_KEYS`).
    """
    base = {
        ":prov/derived-from-atoms": [],
        ":prov/source-documents": [],
        ":prov/contradiction-atoms": [],
        ":prov/proposed-by": {":lineage": ":induced"},
        ":prov/validated-by": [],
        ":prov/entrenchment": 0.5,
        ":prov/status": STATUS_ACTIVE,
        ":prov/llm-repair-calls": 0,
        ":prov/cost-usd": 0.0,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _seed_sidecar(tmp_path: Path, rules: dict[str, dict]) -> Path:
    """Write a sidecar containing ``rules`` and return its path."""
    sidecar = ProvenanceSidecar()
    for rule_id, prov in rules.items():
        sidecar.add_rule_provenance(rule_id, prov)
    path = tmp_path / "induced-theory.prov.edn"
    sidecar.save(path)
    return path


def _load_rule(path: Path, rule_id: str) -> dict:
    sidecar = ProvenanceSidecar.load(path)
    rule = sidecar.lookup(rule_id)
    assert rule is not None, f"rule {rule_id} not in sidecar at {path}"
    return rule


# ===========================================================================
# Z1: revise_theory + paper-retraction contraction
# REQ-REVISE-040, 041, 046
# ===========================================================================


def test_retraction_contracts_rule(tmp_path: Path) -> None:
    """REQ-REVISE-040: retract a paper -> rule's support shrinks -> entrenchment recomputed."""
    prov_path = _seed_sidecar(
        tmp_path,
        {
            ":induced/r1": _prov(**{
                ":prov/derived-from-atoms": ["c-1", "c-2", "c-3"],
                ":prov/source-documents": ["pmid:1", "pmid:2"],
                ":prov/entrenchment": 0.85,
                ":prov/status": STATUS_ACTIVE,
            }),
        },
    )

    report = revise_theory(
        induced_path=None,
        prov_path=prov_path,
        retracted_docs=["pmid:1"],
        contradicting_atoms=[],
    )

    assert report["rules-affected"] >= 0  # transition count
    # Rule's entrenchment should drop (lost half its support).
    rule = _load_rule(prov_path, ":induced/r1")
    assert rule[":prov/entrenchment"] < 0.85
    assert "pmid:1" not in rule[":prov/source-documents"]
    assert "pmid:2" in rule[":prov/source-documents"]


def test_revise_theory_signature_and_in_place_sidecar_mutation(tmp_path: Path) -> None:
    """REQ-REVISE-040: sidecar is mutated in place, induced_path untouched."""
    prov_path = _seed_sidecar(
        tmp_path,
        {
            ":induced/r1": _prov(**{
                ":prov/derived-from-atoms": ["c-1"],
                ":prov/source-documents": ["pmid:1"],
                ":prov/entrenchment": 0.6,
                ":prov/status": STATUS_TENTATIVE,
            }),
        },
    )

    # induced_path may be None — this micro-test exercises sidecar-only revision.
    report = revise_theory(
        induced_path=None,
        prov_path=prov_path,
        retracted_docs=["pmid:1"],
    )
    assert isinstance(report, RevisionReport)

    # File on disk still parses; the rule still exists; quarantined rules persist.
    rule = _load_rule(prov_path, ":induced/r1")
    assert rule is not None  # never silently deleted


def test_unaffected_rule_left_untouched(tmp_path: Path) -> None:
    """REQ-REVISE-041(b): when intersection is empty, the rule keeps its entrenchment."""
    prov_path = _seed_sidecar(
        tmp_path,
        {
            ":induced/r1": _prov(**{
                ":prov/derived-from-atoms": ["c-1", "c-2"],
                ":prov/source-documents": ["pmid:1"],
                ":prov/entrenchment": 0.82,
                ":prov/status": STATUS_ACTIVE,
            }),
            ":induced/r2": _prov(**{
                ":prov/derived-from-atoms": ["c-3"],
                ":prov/source-documents": ["pmid:99"],
                ":prov/entrenchment": 0.75,
                ":prov/status": STATUS_ACTIVE,
            }),
        },
    )

    revise_theory(
        induced_path=None,
        prov_path=prov_path,
        retracted_docs=["pmid:1"],  # only r1 affected
    )

    r2 = _load_rule(prov_path, ":induced/r2")
    assert r2[":prov/entrenchment"] == 0.75
    assert r2[":prov/status"] == STATUS_ACTIVE


def test_single_paper_one_rule_contracts(tmp_path: Path) -> None:
    """REQ-REVISE-046(a): retracted paper supports exactly 1 rule -> only that rule contracts."""
    prov_path = _seed_sidecar(
        tmp_path,
        {
            ":induced/affected": _prov(**{
                ":prov/derived-from-atoms": ["c-1", "c-2"],
                ":prov/source-documents": ["pmid:target", "pmid:other"],
                ":prov/entrenchment": 0.9,
                ":prov/status": STATUS_ACTIVE,
            }),
            ":induced/untouched-a": _prov(**{
                ":prov/derived-from-atoms": ["c-3"],
                ":prov/source-documents": ["pmid:a", "pmid:b"],
                ":prov/entrenchment": 0.8,
                ":prov/status": STATUS_ACTIVE,
            }),
            ":induced/untouched-b": _prov(**{
                ":prov/derived-from-atoms": ["c-4"],
                ":prov/source-documents": ["pmid:c"],
                ":prov/entrenchment": 0.5,
                ":prov/status": STATUS_TENTATIVE,
            }),
        },
    )

    revise_theory(
        induced_path=None,
        prov_path=prov_path,
        retracted_docs=["pmid:target"],
    )

    affected = _load_rule(prov_path, ":induced/affected")
    assert "pmid:target" not in affected[":prov/source-documents"]
    assert affected[":prov/entrenchment"] < 0.9

    a = _load_rule(prov_path, ":induced/untouched-a")
    b = _load_rule(prov_path, ":induced/untouched-b")
    assert a[":prov/entrenchment"] == 0.8
    assert b[":prov/entrenchment"] == 0.5


def test_single_paper_five_rules_contract(tmp_path: Path) -> None:
    """REQ-REVISE-046(b): retracted paper cited by 5 rules -> all 5 contract."""
    rules = {}
    for i in range(5):
        rules[f":induced/r{i}"] = _prov(**{
            ":prov/derived-from-atoms": [f"c-{i}-1", f"c-{i}-2"],
            ":prov/source-documents": ["pmid:shared", f"pmid:rule{i}"],
            ":prov/entrenchment": 0.85,
            ":prov/status": STATUS_ACTIVE,
        })
    prov_path = _seed_sidecar(tmp_path, rules)

    revise_theory(
        induced_path=None,
        prov_path=prov_path,
        retracted_docs=["pmid:shared"],
    )

    for i in range(5):
        rule = _load_rule(prov_path, f":induced/r{i}")
        assert "pmid:shared" not in rule[":prov/source-documents"]
        # Half the support gone -> entrenchment must drop.
        assert rule[":prov/entrenchment"] < 0.85


def test_entrenchment_formula_clamps_to_unit_interval(tmp_path: Path) -> None:
    """REQ-REVISE-041(e): entrenchment SHALL be in [0.0, 1.0] after revision."""
    rules = {
        ":induced/saturated": _prov(**{
            # 15 docs -> doc factor is capped at 1.0
            ":prov/derived-from-atoms": [f"c-{i}" for i in range(20)],
            ":prov/source-documents": [f"pmid:{i}" for i in range(15)],
            ":prov/entrenchment": 0.95,
            ":prov/status": STATUS_ACTIVE,
        }),
        ":induced/empty-after": _prov(**{
            ":prov/derived-from-atoms": ["c-x"],
            ":prov/source-documents": ["pmid:gone"],
            ":prov/entrenchment": 0.7,
            ":prov/status": STATUS_ACTIVE,
        }),
    }
    prov_path = _seed_sidecar(tmp_path, rules)

    revise_theory(
        induced_path=None,
        prov_path=prov_path,
        retracted_docs=["pmid:gone"],
        contradicting_atoms=["c-x"],
    )

    for rule_id in (":induced/saturated", ":induced/empty-after"):
        rule = _load_rule(prov_path, rule_id)
        e = rule[":prov/entrenchment"]
        assert 0.0 <= e <= 1.0, f"{rule_id} entrenchment {e} out of [0,1]"


# ===========================================================================
# Z2: status threshold transitions
# REQ-REVISE-042, 043
# ===========================================================================


def test_status_thresholds_deterministic(tmp_path: Path) -> None:
    """REQ-REVISE-042: status is a deterministic function of entrenchment."""
    # Drive transitions end-to-end with a fixture that crosses both
    # boundaries in a single revision.
    prov_path = _seed_sidecar(
        tmp_path,
        {
            # Will keep enough support to stay above 0.7
            ":induced/stays-active": _prov(**{
                ":prov/derived-from-atoms": [f"c-a-{i}" for i in range(10)],
                ":prov/source-documents": [f"pmid:keep-{i}" for i in range(10)]
                + ["pmid:drop-1"],
                ":prov/entrenchment": 0.95,
                ":prov/status": STATUS_ACTIVE,
                ":prov/validated-by": [{":sat-rate": 0.95}],
            }),
            # 8 docs, lose 4 -> doc factor goes from 0.8 to 0.4, sat 0.9
            # new entrenchment ~ 0.36 -> quarantined
            ":induced/falls-to-quarantine": _prov(**{
                ":prov/derived-from-atoms": ["c-q-1"],
                ":prov/source-documents": [
                    "pmid:q-1",
                    "pmid:q-2",
                    "pmid:q-3",
                    "pmid:q-4",
                    "pmid:q-5",
                    "pmid:q-6",
                    "pmid:q-7",
                    "pmid:q-8",
                ],
                ":prov/entrenchment": 0.72,
                ":prov/status": STATUS_ACTIVE,
                ":prov/validated-by": [{":sat-rate": 0.9}],
            }),
            # 7 docs, lose 1 -> doc factor 0.6, sat 0.9 -> ~0.54 tentative
            ":induced/falls-to-tentative": _prov(**{
                ":prov/derived-from-atoms": ["c-t-1"],
                ":prov/source-documents": [
                    "pmid:t-1",
                    "pmid:t-2",
                    "pmid:t-3",
                    "pmid:t-4",
                    "pmid:t-5",
                    "pmid:t-6",
                    "pmid:t-7",
                ],
                ":prov/entrenchment": 0.7,
                ":prov/status": STATUS_ACTIVE,
                ":prov/validated-by": [{":sat-rate": 0.9}],
            }),
        },
    )

    revise_theory(
        induced_path=None,
        prov_path=prov_path,
        retracted_docs=[
            "pmid:drop-1",
            "pmid:q-5",
            "pmid:q-6",
            "pmid:q-7",
            "pmid:q-8",
            "pmid:t-7",
        ],
    )

    stays = _load_rule(prov_path, ":induced/stays-active")
    falls_q = _load_rule(prov_path, ":induced/falls-to-quarantine")
    falls_t = _load_rule(prov_path, ":induced/falls-to-tentative")

    assert stays[":prov/status"] == STATUS_ACTIVE
    assert stays[":prov/entrenchment"] >= THRESHOLD_ACTIVE

    assert falls_q[":prov/status"] == STATUS_QUARANTINED
    assert falls_q[":prov/entrenchment"] < THRESHOLD_TENTATIVE

    assert falls_t[":prov/status"] == STATUS_TENTATIVE
    assert THRESHOLD_TENTATIVE <= falls_t[":prov/entrenchment"] < THRESHOLD_ACTIVE


def test_status_threshold_boundary_at_0_7_inclusive(tmp_path: Path) -> None:
    """REQ-REVISE-042: ``>= 0.7`` is :active (inclusive boundary).

    Start :active with maximum support; lose one of ten atoms; the
    recomputed entrenchment lands ``>= 0.7`` and the rule stays :active.
    """
    # 10 docs, 10 atoms, sat-rate 1.0 -> doc factor 1.0.
    # After losing 1 atom: sat = 1 - 1/10 = 0.9, entrenchment = 0.9 -> :active.
    prov_path = _seed_sidecar(
        tmp_path,
        {
            ":induced/boundary": _prov(**{
                ":prov/derived-from-atoms": [f"c-{i}" for i in range(10)],
                ":prov/source-documents": [f"pmid:{i}" for i in range(10)],
                ":prov/entrenchment": 1.0,
                ":prov/status": STATUS_ACTIVE,
                ":prov/validated-by": [{":sat-rate": 1.0}],
            }),
        },
    )

    revise_theory(
        induced_path=None,
        prov_path=prov_path,
        contradicting_atoms=["c-0"],
    )
    rule = _load_rule(prov_path, ":induced/boundary")
    assert rule[":prov/entrenchment"] >= THRESHOLD_ACTIVE
    assert rule[":prov/status"] == STATUS_ACTIVE


def test_no_promote_up_in_tier_six(tmp_path: Path) -> None:
    """REQ-REVISE-043: revise_theory SHALL NOT promote a rule's status upward."""
    prov_path = _seed_sidecar(
        tmp_path,
        {
            ":induced/tentative": _prov(**{
                ":prov/derived-from-atoms": ["c-1", "c-orphan"],
                ":prov/source-documents": [f"pmid:{i}" for i in range(15)],
                ":prov/entrenchment": 0.4,  # set artificially low
                ":prov/status": STATUS_TENTATIVE,
                ":prov/validated-by": [{":sat-rate": 1.0}],
            }),
        },
    )

    revise_theory(
        induced_path=None,
        prov_path=prov_path,
        contradicting_atoms=["c-orphan"],
    )

    rule = _load_rule(prov_path, ":induced/tentative")
    # The recomputed entrenchment is high (many docs, full sat-rate)
    # but promote-up is forbidden.
    assert rule[":prov/status"] == STATUS_TENTATIVE


def test_quarantined_rule_persists_in_sidecar(tmp_path: Path) -> None:
    """REQ-REVISE-042: quarantined rules SHALL persist in the sidecar."""
    prov_path = _seed_sidecar(
        tmp_path,
        {
            ":induced/r1": _prov(**{
                ":prov/derived-from-atoms": ["c-1"],
                ":prov/source-documents": ["pmid:1"],
                ":prov/entrenchment": 0.5,
                ":prov/status": STATUS_TENTATIVE,
                ":prov/validated-by": [{":sat-rate": 0.5}],
            }),
        },
    )
    revise_theory(
        induced_path=None,
        prov_path=prov_path,
        retracted_docs=["pmid:1"],
    )

    rule = _load_rule(prov_path, ":induced/r1")
    assert rule is not None  # never deleted
    assert rule[":prov/status"] == STATUS_QUARANTINED


def test_contradicting_atom_downgrades_active_to_tentative(tmp_path: Path) -> None:
    """REQ-REVISE-046(c): contradicting atom on an :active rule -> :tentative.

    Construct a rule near the 0.7 boundary so a single contradicting atom
    pushes it into the [0.4, 0.7) band.
    """
    # 8 docs, 4 atoms, sat-rate 0.9. Doc factor = 0.8. Entrenchment = 0.72.
    # Lose 1 atom -> sat-rate becomes 0.9 * (1 - 1/4) = 0.675; entrenchment
    # = 0.675 * 0.8 = 0.54 -> :tentative.
    prov_path = _seed_sidecar(
        tmp_path,
        {
            ":induced/boundary-active": _prov(**{
                ":prov/derived-from-atoms": ["c-1", "c-2", "c-3", "c-4"],
                ":prov/source-documents": [f"pmid:{i}" for i in range(8)],
                ":prov/entrenchment": 0.72,
                ":prov/status": STATUS_ACTIVE,
                ":prov/validated-by": [{":sat-rate": 0.9}],
            }),
        },
    )

    revise_theory(
        induced_path=None,
        prov_path=prov_path,
        contradicting_atoms=["c-1"],
    )

    rule = _load_rule(prov_path, ":induced/boundary-active")
    assert rule[":prov/status"] == STATUS_TENTATIVE
    assert THRESHOLD_TENTATIVE <= rule[":prov/entrenchment"] < THRESHOLD_ACTIVE


# ===========================================================================
# Z3: full-quarantine warning
# REQ-REVISE-044
# ===========================================================================


def test_full_quarantine_warning_fires(tmp_path: Path, caplog) -> None:
    """REQ-REVISE-044: every rule quarantined in one revision -> warning fires."""
    # 3 rules, each with a single supporting doc that we retract.
    rules = {
        f":induced/r{i}": _prov(**{
            ":prov/derived-from-atoms": [f"c-{i}"],
            ":prov/source-documents": [f"pmid:doc-{i}"],
            ":prov/entrenchment": 0.5,
            ":prov/status": STATUS_TENTATIVE,
            ":prov/validated-by": [{":sat-rate": 0.5}],
        })
        for i in range(3)
    }
    prov_path = _seed_sidecar(tmp_path, rules)

    with caplog.at_level(logging.WARNING, logger="scripts._agm_revision"):
        report = revise_theory(
            induced_path=None,
            prov_path=prov_path,
            retracted_docs=[f"pmid:doc-{i}" for i in range(3)],
        )

    assert report.full_quarantine_warning is True
    assert report.rules_quarantined == 3
    assert report.rules_active == 0
    assert report.rules_tentative == 0

    # The structured warning must name the input counts.
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings, "expected a logging.warning for full quarantine"
    msg = warnings[0].getMessage()
    assert "quarantine" in msg.lower()


def test_no_warning_when_some_rules_remain_active(tmp_path: Path, caplog) -> None:
    """REQ-REVISE-044 (negative): partial quarantine MUST NOT fire the warning."""
    prov_path = _seed_sidecar(
        tmp_path,
        {
            ":induced/survives": _prov(**{
                ":prov/derived-from-atoms": ["c-1"],
                ":prov/source-documents": [f"pmid:k{i}" for i in range(12)],
                ":prov/entrenchment": 0.9,
                ":prov/status": STATUS_ACTIVE,
                ":prov/validated-by": [{":sat-rate": 0.9}],
            }),
            ":induced/dies": _prov(**{
                ":prov/derived-from-atoms": ["c-2"],
                ":prov/source-documents": ["pmid:lonely"],
                ":prov/entrenchment": 0.4,
                ":prov/status": STATUS_TENTATIVE,
                ":prov/validated-by": [{":sat-rate": 0.4}],
            }),
        },
    )

    with caplog.at_level(logging.WARNING, logger="scripts._agm_revision"):
        report = revise_theory(
            induced_path=None,
            prov_path=prov_path,
            retracted_docs=["pmid:lonely"],
        )

    assert report.full_quarantine_warning is False
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert not warnings, "warning fired despite a surviving :active rule"


# ===========================================================================
# REQ-REVISE-045: RevisionReport shape and counts
# ===========================================================================


def test_revision_report_shape_and_counts(tmp_path: Path) -> None:
    """REQ-REVISE-045: report exposes per-status counts + transition count + diff."""
    prov_path = _seed_sidecar(
        tmp_path,
        {
            ":induced/a": _prov(**{
                ":prov/derived-from-atoms": ["c-a"],
                ":prov/source-documents": [f"pmid:a{i}" for i in range(12)],
                ":prov/entrenchment": 0.9,
                ":prov/status": STATUS_ACTIVE,
                ":prov/validated-by": [{":sat-rate": 0.9}],
            }),
            ":induced/b": _prov(**{
                ":prov/derived-from-atoms": ["c-b"],
                ":prov/source-documents": ["pmid:b-target", "pmid:b-keep"],
                ":prov/entrenchment": 0.7,
                ":prov/status": STATUS_ACTIVE,
                ":prov/validated-by": [{":sat-rate": 0.9}],
            }),
            ":induced/c": _prov(**{
                ":prov/derived-from-atoms": ["c-c"],
                ":prov/source-documents": ["pmid:c"],
                ":prov/entrenchment": 0.5,
                ":prov/status": STATUS_TENTATIVE,
            }),
        },
    )

    report = revise_theory(
        induced_path=None,
        prov_path=prov_path,
        retracted_docs=["pmid:b-target"],
    )

    # Shape
    assert isinstance(report, RevisionReport)
    assert isinstance(report.rules_affected, int)
    assert isinstance(report.rules_active, int)
    assert isinstance(report.rules_tentative, int)
    assert isinstance(report.rules_quarantined, int)
    assert isinstance(report.diff_summary, str)
    assert isinstance(report.full_quarantine_warning, bool)

    # Counts add up.
    total = (
        report.rules_active + report.rules_tentative + report.rules_quarantined
    )
    assert total == 3

    # diff_summary should mention only transitioning rules.
    if report.rules_affected > 0:
        assert "->" in report.diff_summary


def test_revision_report_kebab_case_indexing(tmp_path: Path) -> None:
    """REQ-REVISE-045: kebab-case indexing keeps the Phase Z1.1 micro-test contract."""
    prov_path = _seed_sidecar(
        tmp_path,
        {
            ":induced/r1": _prov(**{
                ":prov/derived-from-atoms": ["c-1"],
                ":prov/source-documents": ["pmid:1", "pmid:2"],
                ":prov/entrenchment": 0.85,
                ":prov/status": STATUS_ACTIVE,
                ":prov/validated-by": [{":sat-rate": 0.85}],
            }),
        },
    )

    report = revise_theory(
        induced_path=None,
        prov_path=prov_path,
        retracted_docs=["pmid:1"],
    )

    # Either kebab-case or snake_case must index identically.
    assert report["rules-affected"] == report.rules_affected
    assert report["rules-active"] == report.rules_active
    assert report["rules-tentative"] == report.rules_tentative
    assert report["rules-quarantined"] == report.rules_quarantined
    assert report["diff-summary"] == report.diff_summary
    assert report["full-quarantine-warning"] == report.full_quarantine_warning


# ===========================================================================
# Module-level constants
# ===========================================================================


def test_threshold_constants_match_spec() -> None:
    """REQ-REVISE-042: the published thresholds are 0.7 and 0.4."""
    assert THRESHOLD_ACTIVE == 0.7
    assert THRESHOLD_TENTATIVE == 0.4
    assert DOC_SATURATION == 10.0
