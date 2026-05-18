"""REQ-BOOKLOGIC-040..045: reference docs exist with expected structure."""
from __future__ import annotations

from pathlib import Path

REF = Path(__file__).resolve().parents[1] / "references"


def _has_substring(path: Path, needle: str) -> bool:
    return needle in path.read_text(encoding="utf-8")


def test_atomspace_edn_present():
    p = REF / "atomspace-edn.md"
    assert p.exists()
    assert _has_substring(p, ":expression"), "must document :expression atom shape"
    assert _has_substring(p, ":OPAQUE"), "must document :OPAQUE symbol atom"
    assert _has_substring(p, ":CONTEXT"), "must document :CONTEXT symbol atom"


def test_grounded_atoms_present():
    p = REF / "grounded-atoms.md"
    assert p.exists()
    assert _has_substring(p, "(?P<"), "must document Python regex dialect"
    assert _has_substring(p, "parse-float"), "must mention parse-float helper"


def test_phase_boundaries_present():
    p = REF / "phase-boundaries.md"
    assert p.exists()
    assert _has_substring(p, "predicates.edn"), "must reference predicates.edn boundary"
    assert _has_substring(p, "verdict.edn"), "must reference verdict.edn boundary"


def test_rewrite_rule_style_marks_stub():
    p = REF / "rewrite-rule-style.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8").lower()
    assert "stub" in text, "must explicitly mark egg as stub"


def test_metta_idioms_present():
    p = REF / "metta-idioms.md"
    assert p.exists()
    assert _has_substring(p, "atomspace"), "must mention atomspace"
    assert _has_substring(p, "grounded"), "must mention grounded atoms"


def test_worked_example_walks_seven_form_families():
    p = REF / "worked-examples" / "osmotic-pressure" / "clojure.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    for form in ("defsort", "defpredicate", "deflift", "defconstraint"):
        assert form in text, f"{form} not mentioned in walkthrough"
