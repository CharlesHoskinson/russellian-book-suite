"""REQ-TEST-041: Outcome-Driven Constraint Violation validator.

Phase X's syntactic pre-check for the Tier 6 induction layer. Before a
candidate's support is counted or Z3 is invoked, the validator inspects
the `:assert` body for trivially-true forms that "cover" every atom while
asserting nothing:

  - `(or true ...)`            — a disjunction with a literal-true arm
  - `(and false ...)`          — a conjunction with a literal-false arm
                                 (vacuously true when the rule fires on
                                 unsat; rejected to be safe)
  - `(= X X)`                  — an identity equality

A candidate that matches any of these is rejected with reason
`:trivial-tautology` so it never reaches the solver.

The companion grammar enforcer (`_induction_grammar.cljs`) handles
structural / circular-definition failures; this module owns the
semantic-triviality pre-check. The two run before any solver call.
"""
from __future__ import annotations

from typing import Any

from scripts._edn_reader import Keyword, Symbol


# REQ-INDUCE-046: must stay in sync with `_induction_grammar.cljs`'s
# SUPPORTED-OPERATORS and codegen_axioms.py's _SUPPORTED_ASSERT_HEADS.
_SUPPORTED_OPERATORS = frozenset({
    "=", "~=", "approx=",
    "<", "<=", ">", ">=",
    "+", "-", "*", "/",
    "and", "or", "not", "=>", "ite",
    "sum", "count", "in", "select",
    "forall", "exists",
})


class ValidationResult:
    """Outcome of the syntactic pre-check."""

    def __init__(self, rejected: bool, reason: str | None = None) -> None:
        self.rejected = rejected
        self.reason = reason


def _extract_keyed_value(form: Any, key_name: str) -> Any:
    """Pull the value associated with `:<key_name>` from a defconstraint
    form. The EDN reader parses `(defconstraint :name :k1 v1 :k2 v2 ...)`
    as a list whose elements alternate keyword/value after the rule name;
    this scans the tail for `:key_name` and returns the following value,
    or None if absent."""
    if not isinstance(form, list):
        return None
    items = list(form)
    for i, item in enumerate(items):
        if getattr(item, "name", None) == key_name and i + 1 < len(items):
            return items[i + 1]
    return None


def _terms_equal(a: Any, b: Any) -> bool:
    """Structural equality over EDN terms (lists, keywords, primitives)."""
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


def is_trivial_tautology(assert_form: Any) -> bool:
    """Return True if `assert_form` is a syntactic always-true expression.

    Catches `(or true ...)`, `(and false ...)`, and identity equalities
    `(= X X)`."""
    if not isinstance(assert_form, (list, tuple)):
        return False
    if len(assert_form) < 2:
        return False
    head = assert_form[0]
    head_name = getattr(head, "name", str(head))
    args = list(assert_form[1:])
    if head_name == "or":
        return any(a is True for a in args)
    if head_name == "and":
        return any(a is False for a in args)
    if head_name == "=" and len(args) == 2:
        return _terms_equal(args[0], args[1])
    return False


def validate(candidate: Any) -> ValidationResult:
    """Run the syntactic pre-check on a parsed `defconstraint` form.

    Returns a `ValidationResult` tagged `:trivial-tautology` when the
    `:assert` body is trivially true, else an accepting result."""
    assert_form = _extract_keyed_value(candidate, "assert")
    if assert_form is not None and is_trivial_tautology(assert_form):
        return ValidationResult(rejected=True, reason=":trivial-tautology")
    return ValidationResult(rejected=False)


# ---------------------------------------------------------------------------
# REQ-INDUCE-040: Python grammar gate (mirrors `_induction_grammar.cljs`)
# ---------------------------------------------------------------------------


class GrammarResult:
    """Outcome of the grammar gate. `ok` is True for a conforming form;
    otherwise `tag` carries the grammar-fail keyword (e.g.
    ``:grammar-fail/illegal-op``) the orchestrator routes on."""

    def __init__(self, ok: bool, tag: str | None = None, reason: str | None = None) -> None:
        self.ok = ok
        self.tag = tag
        self.reason = reason


def _head_name(form: Any) -> str | None:
    if isinstance(form, list) and form:
        return getattr(form[0], "name", None) or (
            form[0] if isinstance(form[0], str) else None
        )
    return None


def _is_predicate_call(form: Any) -> bool:
    return isinstance(form, list) and bool(form) and isinstance(form[0], Keyword)


def _is_operator_call(form: Any) -> bool:
    return isinstance(form, list) and bool(form) and isinstance(form[0], Symbol)


def _collect_operators(form: Any) -> set[str]:
    """Collect operator (Symbol) heads from an :assert body, skipping the
    arguments of predicate-calls (those are not operators)."""
    if _is_predicate_call(form):
        out: set[str] = set()
        for sub in form[1:]:
            out |= _collect_operators(sub)
        return out
    if _is_operator_call(form):
        out = {form[0].name}
        for sub in form[1:]:
            out |= _collect_operators(sub)
        return out
    if isinstance(form, list):
        out = set()
        for sub in form:
            out |= _collect_operators(sub)
        return out
    return set()


def _collect_predicates(form: Any) -> set[Keyword]:
    """Collect predicate keywords in head position of predicate-calls."""
    if _is_predicate_call(form):
        out = {form[0]}
        for sub in form[1:]:
            out |= _collect_predicates(sub)
        return out
    if isinstance(form, list):
        out: set[Keyword] = set()
        for sub in form:
            out |= _collect_predicates(sub)
        return out
    return set()


def _contains_term(form: Any, target: Any) -> bool:
    if _terms_equal(form, target):
        return True
    if isinstance(form, list):
        return any(_contains_term(x, target) for x in form)
    if isinstance(form, dict):
        return any(
            _contains_term(k, target) or _contains_term(v, target)
            for k, v in form.items()
        )
    return False


def grammar_conforming(candidate: Any, schema: dict) -> GrammarResult:
    """Python mirror of `_induction_grammar.cljs`'s ``grammar-conforming?``.

    Validates a parsed ``defconstraint`` form against the supported
    operator set and the schema's declared predicates, and rejects a
    self-referential rule (``:assert`` cites its own ``:on-unsat`` defect
    id). Returns the same six-category tags the cljs enforcer uses so the
    Python and CLJS orchestrators route rejections identically.
    """
    if not isinstance(candidate, list) or not candidate:
        return GrammarResult(False, ":grammar-fail/non-edn",
                             "form is not a sequential constraint expression")
    if _head_name(candidate) != "defconstraint":
        return GrammarResult(False, ":grammar-fail/wrong-head",
                             "head must be defconstraint")

    assert_form = _extract_keyed_value(candidate, "assert")
    on_unsat = _extract_keyed_value(candidate, "on-unsat")
    if assert_form is None:
        return GrammarResult(False, ":grammar-fail/wrong-head",
                             ":assert option is required")
    if on_unsat is None:
        return GrammarResult(False, ":grammar-fail/wrong-head",
                             ":on-unsat option is required")

    illegal = _collect_operators(assert_form) - _SUPPORTED_OPERATORS
    if illegal:
        return GrammarResult(False, ":grammar-fail/illegal-op",
                             f"illegal operator(s): {sorted(illegal)}")

    known = set(schema.get(Keyword("predicates"), {}).keys())
    missing = _collect_predicates(assert_form) - known
    if missing:
        return GrammarResult(False, ":grammar-fail/unknown-predicate",
                             f"unknown predicate(s): {sorted(str(m) for m in missing)}")

    defect_id = None
    if isinstance(on_unsat, dict):
        for k, v in on_unsat.items():
            if getattr(k, "name", None) == "defect":
                defect_id = v
                break
    if defect_id is not None and _contains_term(assert_form, defect_id):
        return GrammarResult(False, ":grammar-fail/circular-definition",
                             "assert references its own :on-unsat defect id")

    return GrammarResult(True)
