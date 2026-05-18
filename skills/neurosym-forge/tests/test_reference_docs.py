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


def test_dsl_reference_covers_seven_forms():
    """REQ-BOOKLOGIC-047: DSL reference covers all 7 form families."""
    p = Path(__file__).resolve().parents[3] / "docs" / "booklogic-dsl-reference.md"
    assert p.exists(), f"docs/booklogic-dsl-reference.md missing at {p}"
    text = p.read_text(encoding="utf-8")
    for form in ("defsort", "defpredicate", "deflift", "defrule",
                 "defconstraint", "defquery", "defremedy"):
        assert form in text, f"{form} not covered in DSL reference"


def test_dsl_reference_has_debugging_section():
    """REQ-BOOKLOGIC-048: DSL reference has a Debugging section covering
    the four Tier 1 affordances."""
    p = Path(__file__).resolve().parents[3] / "docs" / "booklogic-dsl-reference.md"
    text = p.read_text(encoding="utf-8")
    for affordance in ("VERIFIER_DEBUG_SMT", "make extract",
                       "VERIFIER_SOLVER_TIMEOUT_MS", ":unknown"):
        assert affordance in text, (
            f"{affordance!r} not mentioned in DSL reference Debugging section"
        )
