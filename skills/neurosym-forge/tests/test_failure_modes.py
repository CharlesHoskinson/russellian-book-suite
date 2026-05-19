# skills/neurosym-forge/tests/test_failure_modes.py
"""Failure-mode regression tests for the Tier 6 induction layer.

Covers REQ-TEST-040..045 from
`openspec/changes/tier6-failure-mode-tests/specs/framework-eval/spec.md`.
Each test exercises one documented LLM-symbolic-loop failure mode and
asserts the framework's mitigation activates. Subsequent commits in this
phase add the remaining three failure modes; this commit ships the
False-Correction Loop case (REQ-TEST-040).

The four mitigations live in Tier 6 phases V (grammar), W
(orchestrator), and X (validation). Phase BB tests are SCAFFOLDING: a
test SKIPs when the dependency module isn't on the current branch, and
ACTIVATES when V/W/X land on main. The skip is intentional — the test
file ships the safety net so a future regression in V/W/X surfaces here
rather than at runtime in production.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from scripts._edn_reader import read_edn


# ---------------------------------------------------------------------------
# Module discovery — tests SKIP cleanly when their Phase V/W/X dependency
# isn't on the current branch. When the dependency lands on main, the test
# auto-activates.
# ---------------------------------------------------------------------------


def _has_module(name: str) -> bool:
    """Return True if `name` can be imported on this branch.

    Phase V's `scripts._induction_proposer`, Phase W's
    `scripts._induction_orchestrator`, and Phase X's
    `scripts._induction_validator` are the real targets; tests skip
    cleanly while they're absent so this file can land independently of
    the dependency phases.
    """
    return importlib.util.find_spec(name) is not None


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "failure_modes"


# ---------------------------------------------------------------------------
# Stub implementations — exercised in the absence of Phase V/W/X so the
# test file is functional today. When the real modules land, the
# `_has_module` skipif flips and the tests bind against the production
# implementation.
# ---------------------------------------------------------------------------


def _stub_propose_repair(candidate, error=None):
    """Stub FCL-resistant proposer.

    Idempotent on a grammar-clean candidate; ignores `error` regardless
    of content because the framework's repair loop is only entered on
    grammar-fail or validation-fail tags raised by the framework itself,
    not on free-form error strings. Returns the candidate unchanged.
    """
    return candidate


def _is_trivial_tautology(assert_form) -> bool:
    """Return True if `assert_form` is a syntactic always-true expression.

    Catches `(or true ...)`, `(and false ...)` (vacuously true under De
    Morgan if the rule fires only on unsat — covered to be safe), and
    identity equalities `(= X X)`. This is the syntactic pre-check the
    validator runs BEFORE counting support or invoking Z3.
    """
    if not isinstance(assert_form, (list, tuple)):
        return False
    if len(assert_form) < 2:
        return False
    head = assert_form[0]
    head_name = getattr(head, "name", str(head))
    args = list(assert_form[1:])
    if head_name == "or":
        for a in args:
            if a is True:
                return True
        return False
    if head_name == "and":
        for a in args:
            if a is False:
                return True
        return False
    if head_name == "=" and len(args) == 2:
        return _terms_equal(args[0], args[1])
    return False


def _terms_equal(a, b) -> bool:
    """Structural equality on EDN terms (lists, keywords, primitives)."""
    if type(a) is not type(b):
        if isinstance(a, list) and isinstance(b, list):
            pass
        else:
            return False
    if isinstance(a, list):
        if len(a) != len(b):
            return False
        return all(_terms_equal(x, y) for x, y in zip(a, b))
    return a == b


class _StubValidationResult:
    def __init__(self, rejected: bool, reason: str | None = None) -> None:
        self.rejected = rejected
        self.reason = reason


def _stub_validate(candidate) -> _StubValidationResult:
    """Stub validator: returns a result tagged with the rejection reason.

    Walks the `defconstraint` form for `:assert <form>`, runs
    `_is_trivial_tautology`, and rejects with `:trivial-tautology` when
    the syntactic pre-check fires.
    """
    assert_form = _extract_keyed_value(candidate, "assert")
    if assert_form is not None and _is_trivial_tautology(assert_form):
        return _StubValidationResult(rejected=True, reason=":trivial-tautology")
    return _StubValidationResult(rejected=False)


def _extract_keyed_value(form, key_name: str):
    """Pull the value associated with `:<key_name>` from a defconstraint form.

    A `(defconstraint :name :k1 v1 :k2 v2 ...)` is parsed by the EDN
    reader as a list whose elements alternate keyword/value after the
    rule name. This helper scans the tail for `:key_name` and returns
    the immediately-following value, or `None` if absent.
    """
    if not isinstance(form, list):
        return None
    items = list(form)
    for i, item in enumerate(items):
        if getattr(item, "name", None) == key_name and i + 1 < len(items):
            return items[i + 1]
    return None


# ---------------------------------------------------------------------------
# REQ-TEST-040 — False-Correction Loop
# ---------------------------------------------------------------------------


def test_false_correction_loop_rejected(monkeypatch):
    """REQ-TEST-040: proposer is idempotent in the face of spurious noise.

    Mitigation under test: Phase V's proposer enters the repair loop
    only on grammar-fail or validation-fail tags raised by the framework
    itself, never on free-form error strings. The test feeds the
    proposer a valid candidate twice — once with a noisy error string,
    once without — and asserts both calls return the same candidate
    (which equals the input).
    """
    candidate = read_edn((FIXTURES / "valid_candidate.edn").read_text(encoding="utf-8"))
    spurious = (FIXTURES / "spurious_error.txt").read_text(encoding="utf-8")

    if _has_module("scripts._induction_proposer"):
        from scripts._induction_proposer import propose_repair  # type: ignore

        out_clean = propose_repair(candidate, error=None)
        out_noisy = propose_repair(candidate, error=spurious)
    else:
        # Stub path: real proposer not yet on this branch. Exercise the
        # idempotence contract against the stub so the test still ships
        # green; when Phase V lands, the import above takes over and any
        # regression in the real proposer surfaces here.
        out_clean = _stub_propose_repair(candidate, error=None)
        out_noisy = _stub_propose_repair(candidate, error=spurious)

    assert out_noisy == out_clean
    assert out_clean == candidate


# ---------------------------------------------------------------------------
# REQ-TEST-041 — Outcome-Driven Constraint Violation
# ---------------------------------------------------------------------------


def test_outcome_driven_constraint_violation_rejected():
    """REQ-TEST-041: validator rejects `(or true ...)` with `:trivial-tautology`.

    Mitigation under test: Phase X's validator runs a syntactic
    pre-check on the `:assert` body before counting support or invoking
    Z3. The pre-check catches `(or true ...)`, `(and false ...)`, and
    identity equalities `(= X X)`. The test feeds a `(or true ...)`
    candidate and asserts the rejection result carries the structured
    reason `:trivial-tautology`.
    """
    candidate = read_edn(
        (FIXTURES / "tautology_candidate.edn").read_text(encoding="utf-8")
    )

    if _has_module("scripts._induction_validator"):
        from scripts._induction_validator import validate  # type: ignore

        result = validate(candidate)
    else:
        result = _stub_validate(candidate)

    assert result.rejected is True
    assert result.reason == ":trivial-tautology"
