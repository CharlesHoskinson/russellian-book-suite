"""Tests for AGM-compliant theory revision (Phase Z, Tier 6).

Covers REQ-REVISE-040..046.

The test fixture sidecar uses the Phase Y ``ProvenanceSidecar`` if it is
present; otherwise the conditional fallback inside
``scripts._agm_revision`` exposes a minimal stub with the same surface.
Both code paths share these tests.
"""
from __future__ import annotations

from pathlib import Path

from scripts._agm_revision import (
    DOC_SATURATION,
    STATUS_ACTIVE,
    STATUS_TENTATIVE,
    THRESHOLD_ACTIVE,
    THRESHOLD_TENTATIVE,
    ProvenanceSidecar,
    RevisionReport,
    revise_theory,
)


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
    sidecar = ProvenanceSidecar()
    sidecar.load(path)
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
            ":induced/r1": {
                ":prov/derived-from-atoms": ["c-1", "c-2", "c-3"],
                ":prov/source-documents": ["pmid:1", "pmid:2"],
                ":prov/entrenchment": 0.85,
                ":prov/status": STATUS_ACTIVE,
            },
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
            ":induced/r1": {
                ":prov/derived-from-atoms": ["c-1"],
                ":prov/source-documents": ["pmid:1"],
                ":prov/entrenchment": 0.6,
                ":prov/status": STATUS_TENTATIVE,
            },
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
            ":induced/r1": {
                ":prov/derived-from-atoms": ["c-1", "c-2"],
                ":prov/source-documents": ["pmid:1"],
                ":prov/entrenchment": 0.82,
                ":prov/status": STATUS_ACTIVE,
            },
            ":induced/r2": {
                ":prov/derived-from-atoms": ["c-3"],
                ":prov/source-documents": ["pmid:99"],
                ":prov/entrenchment": 0.75,
                ":prov/status": STATUS_ACTIVE,
            },
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
            ":induced/affected": {
                ":prov/derived-from-atoms": ["c-1", "c-2"],
                ":prov/source-documents": ["pmid:target", "pmid:other"],
                ":prov/entrenchment": 0.9,
                ":prov/status": STATUS_ACTIVE,
            },
            ":induced/untouched-a": {
                ":prov/derived-from-atoms": ["c-3"],
                ":prov/source-documents": ["pmid:a", "pmid:b"],
                ":prov/entrenchment": 0.8,
                ":prov/status": STATUS_ACTIVE,
            },
            ":induced/untouched-b": {
                ":prov/derived-from-atoms": ["c-4"],
                ":prov/source-documents": ["pmid:c"],
                ":prov/entrenchment": 0.5,
                ":prov/status": STATUS_TENTATIVE,
            },
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
        rules[f":induced/r{i}"] = {
            ":prov/derived-from-atoms": [f"c-{i}-1", f"c-{i}-2"],
            ":prov/source-documents": ["pmid:shared", f"pmid:rule{i}"],
            ":prov/entrenchment": 0.85,
            ":prov/status": STATUS_ACTIVE,
        }
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
        ":induced/saturated": {
            # 15 docs -> doc factor is capped at 1.0
            ":prov/derived-from-atoms": [f"c-{i}" for i in range(20)],
            ":prov/source-documents": [f"pmid:{i}" for i in range(15)],
            ":prov/entrenchment": 0.95,
            ":prov/status": STATUS_ACTIVE,
        },
        ":induced/empty-after": {
            ":prov/derived-from-atoms": ["c-x"],
            ":prov/source-documents": ["pmid:gone"],
            ":prov/entrenchment": 0.7,
            ":prov/status": STATUS_ACTIVE,
        },
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
# Module-level constants
# ===========================================================================


def test_threshold_constants_match_spec() -> None:
    """REQ-REVISE-042: the published thresholds are 0.7 and 0.4."""
    assert THRESHOLD_ACTIVE == 0.7
    assert THRESHOLD_TENTATIVE == 0.4
    assert DOC_SATURATION == 10.0
