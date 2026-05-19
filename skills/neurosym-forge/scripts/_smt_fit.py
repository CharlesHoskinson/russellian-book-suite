"""SMT-based numeric parameter fitter for Tier 6 induced rules.

The Tier 6 candidate-generation stage emits structural BookLogic rules
with placeholders for tolerances (``:tolerance ?eps``). This module
fits those placeholders to concrete values by encoding the rule as a
Z3 ``Optimize`` problem over the training atomspace and minimising the
candidate's numeric parameters.

REQ-INDUCE-060, 061, 065.

AST shape
---------
The fitter expects a *pre-processed* rule AST: a nested ``tuple`` whose
leaves are either:

* ``str``      — a predicate name (e.g. ``"basic-reproduction-number"``),
  an operator (``"+"``, ``"-"``, ``"*"``, ``"/"``), a comparator
  (``"approx="``, ``">="``, ``"<="``, ``">"``, ``"<"``, ``"="``), or a
  fit-variable name beginning with ``?`` (e.g. ``"?eps"``);
* ``int`` or ``float`` — a numeric literal.

Predicate atoms appear as ``("predicate-name", "?var")``; the variable
slot is currently unused by the fitter (atom selection is the
orchestrator's responsibility — the fitter receives an iterable of
already-bound ``atoms``).

A representative AST::

    ("approx=",
        ("herd-immunity-threshold", "?s"),
        ("-", 1.0, ("/", 1.0, ("basic-reproduction-number", "?s"))),
        ":tolerance", "?eps")

The orchestrator is responsible for translating EDN forms / Keywords
into this tuple-of-strings shape before calling the fitter.

Atoms
-----
``atoms`` is an iterable of dicts mapping predicate names (matching the
leaf tuple's first element) to numeric values::

    [{"basic-reproduction-number": 1.5,
      "herd-immunity-threshold": 0.33},
     ...]

Return values
-------------
* ``fit_tolerance(rule_ast, atoms) -> float | None``

``None`` covers:

* **unsat** — no finite assignment satisfies the rule on every atom;
* **structural failure** — the AST referenced a predicate absent from
  some atom, or contained an unexpected node shape.

A structured rejection reason is attached as
``fit_tolerance.last_reason`` after each call (the orchestrator reads
this to build the candidate's post-mortem record).
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

import z3

# Comparators recognised at the AST root. Anything else is treated as an
# unsupported rule shape and yields :smt-unsupported.
_COMPARATORS = frozenset({"approx=", ">=", "<=", ">", "<", "=", "=="})
_ARITHMETIC = frozenset({"+", "-", "*", "/"})


class FitReason(dict):
    """Structured rejection / success reason.

    Subclasses ``dict`` so the orchestrator can serialise it directly
    via the EDN writer. Keys are kept as plain ``str`` colons to match
    the framework's existing structured-reason convention.
    """

    pass


def _is_fit_var(node: Any) -> bool:
    return isinstance(node, str) and node.startswith("?")


def _is_keyword(node: Any) -> bool:
    """A ``:tolerance``-style keyword token (not a predicate atom)."""
    return isinstance(node, str) and node.startswith(":")


def _collect_fit_vars(node: Any, sink: list[str]) -> None:
    if _is_fit_var(node):
        if node not in sink:
            sink.append(node)
        return
    if isinstance(node, tuple):
        for child in node:
            _collect_fit_vars(child, sink)


def _appears_outside_predicate_subject(node: Any, var: str) -> bool:
    """``True`` if ``var`` appears anywhere except as the subject slot of
    a ``(predicate-name ?subject)`` 2-tuple."""
    if isinstance(node, tuple):
        if (len(node) == 2
                and isinstance(node[0], str)
                and not node[0].startswith(("?", ":"))
                and node[0] not in _ARITHMETIC
                and node[0] not in _COMPARATORS
                and node[1] == var):
            # This is the subject slot — does NOT count.
            return False
        for child in node:
            if _appears_outside_predicate_subject(child, var):
                return True
        return False
    return node == var


def _expr_for(node: Any, atom: Mapping[str, float], z3_vars: dict[str, Any]):
    """Lower an AST node to a Z3 real-arithmetic expression for one atom.

    Returns ``(expr, error_reason_or_None)``. On structural failure the
    expression is ``None`` and the reason carries the offending node.
    """
    if isinstance(node, bool):
        # bool is a subclass of int — guard explicitly.
        return None, FitReason({":phase": ":smt-fit",
                                ":reason": ":smt-unsupported",
                                ":node": repr(node)})
    if isinstance(node, (int, float)):
        return z3.RealVal(node), None

    if _is_fit_var(node):
        return z3_vars[node], None

    if _is_keyword(node):
        return None, FitReason({":phase": ":smt-fit",
                                ":reason": ":smt-keyword-as-value",
                                ":token": node})

    if isinstance(node, tuple):
        if len(node) == 0:
            return None, FitReason({":phase": ":smt-fit",
                                    ":reason": ":smt-empty-form"})
        head = node[0]
        if not isinstance(head, str):
            return None, FitReason({":phase": ":smt-fit",
                                    ":reason": ":smt-non-string-head",
                                    ":head": repr(head)})

        if head in _ARITHMETIC:
            args = []
            for child in node[1:]:
                expr, err = _expr_for(child, atom, z3_vars)
                if err is not None:
                    return None, err
                args.append(expr)
            if not args:
                return None, FitReason({":phase": ":smt-fit",
                                        ":reason": ":smt-arity-zero",
                                        ":op": head})
            if head == "+":
                acc = args[0]
                for a in args[1:]:
                    acc = acc + a
                return acc, None
            if head == "-":
                if len(args) == 1:
                    return -args[0], None
                acc = args[0]
                for a in args[1:]:
                    acc = acc - a
                return acc, None
            if head == "*":
                acc = args[0]
                for a in args[1:]:
                    acc = acc * a
                return acc, None
            if head == "/":
                if len(args) != 2:
                    return None, FitReason({":phase": ":smt-fit",
                                            ":reason": ":smt-div-arity",
                                            ":argc": len(args)})
                return args[0] / args[1], None

        # Predicate atom: (predicate-name "?subject").
        if len(node) == 2 and isinstance(node[1], str):
            name = head
            if name not in atom:
                return None, FitReason({":phase": ":smt-fit",
                                        ":reason": ":smt-missing-predicate",
                                        ":predicate": name})
            value = atom[name]
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return None, FitReason({":phase": ":smt-fit",
                                        ":reason": ":smt-non-numeric-atom-value",
                                        ":predicate": name,
                                        ":value": repr(value)})
            return z3.RealVal(value), None

        return None, FitReason({":phase": ":smt-fit",
                                ":reason": ":smt-unknown-form",
                                ":head": head,
                                ":arity": len(node) - 1})

    return None, FitReason({":phase": ":smt-fit",
                            ":reason": ":smt-unsupported",
                            ":node": repr(node)})


def _decompose_rule(rule_ast: tuple):
    """Split a rule into ``(comparator, lhs, rhs, kwargs)``.

    ``kwargs`` collects ``:tolerance ?eps`` style trailing pairs so the
    fitter knows which variable is the tolerance.
    """
    if not isinstance(rule_ast, tuple) or len(rule_ast) < 3:
        return None, None, None, {}
    head = rule_ast[0]
    if not isinstance(head, str) or head not in _COMPARATORS:
        return None, None, None, {}
    lhs = rule_ast[1]
    rhs = rule_ast[2]
    kwargs: dict[str, str] = {}
    rest = list(rule_ast[3:])
    while rest:
        key = rest.pop(0)
        if not _is_keyword(key):
            break
        if not rest:
            break
        val = rest.pop(0)
        if isinstance(val, str) and val.startswith("?"):
            kwargs[key] = val
    return head, lhs, rhs, kwargs


def _per_atom_constraint(comp, lhs, rhs, kwargs, atom, z3_vars):
    lhs_expr, err = _expr_for(lhs, atom, z3_vars)
    if err is not None:
        return None, err
    rhs_expr, err = _expr_for(rhs, atom, z3_vars)
    if err is not None:
        return None, err

    if comp == "approx=":
        tol_var = kwargs.get(":tolerance")
        if tol_var is None:
            return None, FitReason({":phase": ":smt-fit",
                                    ":reason": ":smt-missing-tolerance"})
        eps = z3_vars[tol_var]
        diff = lhs_expr - rhs_expr
        return z3.And(diff <= eps, -diff <= eps), None
    if comp in (">", ">="):
        return (lhs_expr > rhs_expr) if comp == ">" else (lhs_expr >= rhs_expr), None
    if comp in ("<", "<="):
        return (lhs_expr < rhs_expr) if comp == "<" else (lhs_expr <= rhs_expr), None
    if comp in ("=", "=="):
        return lhs_expr == rhs_expr, None

    return None, FitReason({":phase": ":smt-fit",
                            ":reason": ":smt-unsupported-comparator",
                            ":comparator": comp})


def _model_value(model, var) -> float:
    """Extract a float from a Z3 ``Real`` model entry."""
    raw = model[var]
    if raw is None:
        return float("nan")
    try:
        text = raw.as_decimal(20).rstrip("?")
        return float(text)
    except (AttributeError, ValueError):
        pass
    try:
        frac = raw.as_fraction()
        return float(frac.numerator) / float(frac.denominator)
    except Exception:  # noqa: BLE001
        return float("nan")


def fit_tolerance(rule_ast: tuple,
                  atoms: Iterable[Mapping[str, float]],
                  *,
                  max_eps: float | None = None) -> float | None:
    """Return the minimum tolerance ε satisfying ``rule_ast`` on every atom.

    REQ-INDUCE-060, 061.

    Parameters
    ----------
    rule_ast :
        A pre-processed BookLogic rule AST (see module docstring).
    atoms :
        Iterable of dicts mapping predicate names to numeric values.
    max_eps :
        Optional hard upper bound on ε. When supplied, the optimiser
        adds ``eps <= max_eps``; if no satisfying ε ≤ ``max_eps``
        exists, the fit reports unsat and returns ``None``. This lets
        callers reject vacuously loose fits (the deep-research reports
        flag this as the NUMSYNTH "vacuous-bound" failure mode).

    Returns
    -------
    ``float`` minimum ε, or ``None`` on unsat / structural failure.
    The structured rejection reason is stored on
    ``fit_tolerance.last_reason``.
    """
    fit_tolerance.last_reason = None  # type: ignore[attr-defined]
    comp, lhs, rhs, kwargs = _decompose_rule(rule_ast)
    if comp is None:
        fit_tolerance.last_reason = FitReason({  # type: ignore[attr-defined]
            ":phase": ":smt-fit",
            ":reason": ":smt-unsupported-rule",
        })
        return None
    if comp != "approx=":
        fit_tolerance.last_reason = FitReason({  # type: ignore[attr-defined]
            ":phase": ":smt-fit",
            ":reason": ":smt-not-approx-rule",
            ":comparator": comp,
        })
        return None

    tol_var = kwargs.get(":tolerance")
    if tol_var is None:
        fit_tolerance.last_reason = FitReason({  # type: ignore[attr-defined]
            ":phase": ":smt-fit",
            ":reason": ":smt-missing-tolerance",
        })
        return None

    fit_vars: list[str] = []
    _collect_fit_vars(rule_ast, fit_vars)
    fit_vars = [v for v in fit_vars
                if v == tol_var
                or _appears_outside_predicate_subject(rule_ast, v)]
    z3_vars = {v: z3.Real(v.lstrip("?")) for v in fit_vars}

    atom_list = list(atoms)
    if not atom_list:
        fit_tolerance.last_reason = FitReason({  # type: ignore[attr-defined]
            ":phase": ":smt-fit",
            ":reason": ":smt-no-atoms",
        })
        return None

    opt = z3.Optimize()
    opt.add(z3_vars[tol_var] > 0)
    if max_eps is not None:
        opt.add(z3_vars[tol_var] <= z3.RealVal(max_eps))

    for atom in atom_list:
        constraint, err = _per_atom_constraint(
            comp, lhs, rhs, kwargs, atom, z3_vars
        )
        if err is not None:
            fit_tolerance.last_reason = err  # type: ignore[attr-defined]
            return None
        opt.add(constraint)

    opt.minimize(z3_vars[tol_var])
    result = opt.check()
    if result == z3.sat:
        eps = _model_value(opt.model(), z3_vars[tol_var])
        fit_tolerance.last_reason = FitReason({  # type: ignore[attr-defined]
            ":phase": ":smt-fit",
            ":reason": ":smt-sat",
            ":value": eps,
        })
        return eps
    fit_tolerance.last_reason = FitReason({  # type: ignore[attr-defined]
        ":phase": ":smt-fit",
        ":reason": ":smt-unsat",
    })
    return None


fit_tolerance.last_reason = None  # type: ignore[attr-defined]


__all__ = [
    "fit_tolerance",
    "FitReason",
]
