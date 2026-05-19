"""SMT-based numeric parameter fitter for Tier 6 induced rules.

The Tier 6 candidate-generation stage emits structural BookLogic rules
with placeholders for tolerances (``:tolerance ?eps``) and thresholds
(``(>= (:x ?d) ?N)``). This module fits those placeholders to concrete
values by encoding the rule as a Z3 ``Optimize`` problem over the
training atomspace and minimising the candidate's numeric parameters.

REQ-INDUCE-060..065 (Tier 6 — SMT numeric fitting).

AST shape
---------
The fitter expects a *pre-processed* rule AST: a nested ``tuple`` whose
leaves are either:

* ``str``      — a predicate name (e.g. ``"basic-reproduction-number"``),
  an operator (``"+"``, ``"-"``, ``"*"``, ``"/"``), a comparator
  (``"approx="``, ``">="``, ``"<="``, ``">"``, ``"<"``, ``"="``), or a
  fit-variable name beginning with ``?`` (e.g. ``"?eps"``, ``"?N"``);
* ``int`` or ``float`` — a numeric literal.

Predicate atoms appear as ``("predicate-name", "?var")``; the variable
slot is currently unused by the fitter (atom selection is the
orchestrator's responsibility — the fitter receives an iterable of
already-bound ``atoms``).

Tolerance / threshold parameters appear as ``?``-prefixed strings.
The fitter discovers them by walking the AST.

A representative AST::

    ("approx=",
        ("herd-immunity-threshold", "?s"),
        ("-", 1.0, ("/", 1.0, ("basic-reproduction-number", "?s"))),
        ":tolerance", "?eps")

The orchestrator is responsible for translating EDN forms / Keywords
into this tuple-of-strings shape before calling the fitter. Keyword
inputs are accepted via ``str(keyword)`` (e.g. ``Keyword("tolerance")``
becomes ``":tolerance"``).

Atoms
-----
``atoms`` is an iterable of dicts mapping predicate names (matching the
leaf tuple's first element) to numeric values. For the herd-immunity
example::

    [{"basic-reproduction-number": 1.5,
      "herd-immunity-threshold": 0.33},
     ...]

Return values
-------------
* ``fit_tolerance(rule_ast, atoms) -> float | None``
* ``fit_numeric_params(rule_ast, atoms) -> dict[str, float] | None``

``None`` covers three cases:

* **unsat** — no finite assignment satisfies the rule on every atom;
* **unknown / timeout** — Z3 returned ``unknown`` within
  ``VERIFIER_INDUCTION_FIT_TIMEOUT_MS``;
* **structural failure** — the AST referenced a predicate absent from
  some atom, or contained an unexpected node shape.

A structured rejection reason is attached as
``fit_tolerance.last_reason`` / ``fit_numeric_params.last_reason``
after each call (the orchestrator reads this to build the candidate's
post-mortem record).
"""
from __future__ import annotations

import os
from typing import Any, Iterable, Mapping

import z3

DEFAULT_TIMEOUT_MS = 10_000
TIMEOUT_ENV_VAR = "VERIFIER_INDUCTION_FIT_TIMEOUT_MS"

# Comparators recognised at the AST root. Anything else is treated as an
# unsupported rule shape and yields :smt-unsupported.
_COMPARATORS = frozenset({"approx=", ">=", "<=", ">", "<", "=", "=="})
_ARITHMETIC = frozenset({"+", "-", "*", "/"})


class FitReason(dict):
    """Structured rejection / success reason.

    Subclasses ``dict`` so the orchestrator can serialise it directly
    via the EDN writer. Keys are kept as plain ``str`` colons to match
    the framework's existing structured-reason convention (see
    `_cli_errors.py`).
    """

    pass


def _read_timeout_ms() -> int:
    raw = os.environ.get(TIMEOUT_ENV_VAR)
    if raw is None or raw == "":
        return DEFAULT_TIMEOUT_MS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_TIMEOUT_MS
    return value if value > 0 else DEFAULT_TIMEOUT_MS


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


def _expr_for(node: Any, atom: Mapping[str, float], z3_vars: dict[str, Any]):
    """Lower an AST node to a Z3 real-arithmetic expression for one atom.

    Returns ``(expr, error_reason_or_None)``. On structural failure the
    expression is ``None`` and the reason carries the offending node.
    """
    # Numeric literal.
    if isinstance(node, bool):
        # bool is a subclass of int — guard explicitly.
        return None, FitReason({":phase": ":smt-fit",
                                ":reason": ":smt-unsupported",
                                ":node": repr(node)})
    if isinstance(node, (int, float)):
        return z3.RealVal(node), None

    # Fit-variable reference.
    if _is_fit_var(node):
        return z3_vars[node], None

    # Keyword tokens (`:tolerance`) are not values — they should never
    # be lowered directly.
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

        # Arithmetic.
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

        # Predicate atom: (predicate-name "?subject"). The "?subject"
        # slot is informational; the fitter looks up the atom by name.
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


def _decompose_rule(rule_ast: tuple) -> tuple[str, Any, Any, dict[str, str]]:
    """Split a rule into (comparator, lhs, rhs, kwargs).

    ``kwargs`` collects ``:tolerance ?eps`` style trailing pairs so the
    fitter knows which variable is the tolerance (priority-1 in Pareto).
    Returns ``(None, None, None, {})`` on structural failure.
    """
    if not isinstance(rule_ast, tuple) or len(rule_ast) < 3:
        return None, None, None, {}  # type: ignore[return-value]
    head = rule_ast[0]
    if not isinstance(head, str) or head not in _COMPARATORS:
        return None, None, None, {}  # type: ignore[return-value]
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


def _build_optimize(rule_ast: tuple, atoms: Iterable[Mapping[str, float]]
                    ) -> tuple[z3.Optimize, dict[str, Any],
                               list[str], str, FitReason | None]:
    """Construct the Z3 Optimize problem.

    Returns ``(opt, z3_vars, fit_vars, comparator, error_or_None)``.
    On structural failure the optimiser is partial / unusable and the
    reason describes the failure.
    """
    comp, lhs, rhs, kwargs = _decompose_rule(rule_ast)
    if comp is None:
        return (None,  # type: ignore[return-value]
                {}, [], "",
                FitReason({":phase": ":smt-fit",
                           ":reason": ":smt-unsupported-rule"}))

    fit_vars: list[str] = []
    _collect_fit_vars(rule_ast, fit_vars)
    # Drop predicate-subject variables: they appear *inside* atom
    # tuples ``("predicate", "?s")`` and are not fit parameters.
    fit_vars = [v for v in fit_vars
                if v in set(kwargs.values())
                or _appears_outside_predicate_subject(rule_ast, v)]

    if not fit_vars:
        return (None,  # type: ignore[return-value]
                {}, [], comp,
                FitReason({":phase": ":smt-fit",
                           ":reason": ":smt-no-fit-vars"}))

    z3_vars = {v: z3.Real(v.lstrip("?")) for v in fit_vars}
    opt = z3.Optimize()

    # Tolerances are positive by definition.
    tolerance_vars = set(kwargs.values())
    for v in tolerance_vars:
        if v in z3_vars:
            opt.add(z3_vars[v] > 0)

    atom_list = list(atoms)
    if not atom_list:
        return (None,  # type: ignore[return-value]
                {}, [], comp,
                FitReason({":phase": ":smt-fit",
                           ":reason": ":smt-no-atoms"}))

    for atom in atom_list:
        constraint, err = _per_atom_constraint(
            comp, lhs, rhs, kwargs, atom, z3_vars
        )
        if err is not None:
            return None, {}, [], comp, err  # type: ignore[return-value]
        opt.add(constraint)

    return opt, z3_vars, fit_vars, comp, None


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


def _per_atom_constraint(comp: str, lhs: Any, rhs: Any,
                         kwargs: dict[str, str],
                         atom: Mapping[str, float],
                         z3_vars: dict[str, Any]):
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
    """Extract a float from a Z3 ``Real`` model entry.

    Uses ``as_decimal(20)`` and strips Z3's trailing ``?`` (which marks
    "more digits available"). Falls back to ``as_fraction`` if decimal
    parsing fails.
    """
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


def _tolerance_first_key(var: str, tolerance_vars: set[str]) -> tuple[int, str]:
    """Pareto-front ordering: tolerance-like vars minimised first."""
    is_tolerance = 0 if var in tolerance_vars else 1
    return (is_tolerance, var)


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
    ``float`` minimum ε, or ``None`` on unsat / timeout / structural
    failure. The structured rejection reason is stored on
    ``fit_tolerance.last_reason``.
    """
    fit_tolerance.last_reason = None  # type: ignore[attr-defined]
    opt, z3_vars, fit_vars, comp, err = _build_optimize(rule_ast, atoms)
    if err is not None:
        fit_tolerance.last_reason = err  # type: ignore[attr-defined]
        return None
    if comp != "approx=":
        fit_tolerance.last_reason = FitReason({  # type: ignore[attr-defined]
            ":phase": ":smt-fit",
            ":reason": ":smt-not-approx-rule",
            ":comparator": comp,
        })
        return None

    _, lhs_unused, rhs_unused, kwargs = _decompose_rule(rule_ast)
    del lhs_unused, rhs_unused
    tol_var = kwargs.get(":tolerance")
    if tol_var is None or tol_var not in z3_vars:
        fit_tolerance.last_reason = FitReason({  # type: ignore[attr-defined]
            ":phase": ":smt-fit",
            ":reason": ":smt-missing-tolerance",
        })
        return None

    if max_eps is not None:
        opt.add(z3_vars[tol_var] <= z3.RealVal(max_eps))

    timeout_ms = _read_timeout_ms()
    opt.set("timeout", timeout_ms)
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
    if result == z3.unknown:
        fit_tolerance.last_reason = FitReason({  # type: ignore[attr-defined]
            ":phase": ":smt-fit",
            ":reason": ":smt-timeout",
            ":timeout-ms": timeout_ms,
        })
        return None
    fit_tolerance.last_reason = FitReason({  # type: ignore[attr-defined]
        ":phase": ":smt-fit",
        ":reason": ":smt-unsat",
    })
    return None


fit_tolerance.last_reason = None  # type: ignore[attr-defined]


def fit_numeric_params(rule_ast: tuple,
                       atoms: Iterable[Mapping[str, float]],
                       *,
                       upper_bounds: Mapping[str, float] | None = None,
                       ) -> dict[str, float] | None:
    """Fit every ``?``-prefixed numeric parameter via lex-min Pareto.

    REQ-INDUCE-062.

    Pareto priority (lowest index minimised first):

    1. Tolerance-tagged variables (``:tolerance ?eps`` and any other
       keyword-tagged parameter): tighter is better.
    2. All other fit variables: smaller absolute value is preferred.
       (Smaller threshold is the tighter rule on a ``>=`` clause; the
       symmetry holds for ``<=`` after sign flip — orchestrators
       wanting maximum-threshold fits should negate before calling.)

    Parameters
    ----------
    rule_ast, atoms :
        See ``fit_tolerance``.
    upper_bounds :
        Optional per-variable upper bound (``{":tolerance ?eps": 1.0}``
        becomes ``eps <= 1.0``). Same semantic as ``max_eps`` on the
        single-parameter fitter.

    Returns
    -------
    Dict mapping the AST variable name (e.g. ``"?eps"``) to the fitted
    float, or ``None`` on unsat / timeout / structural failure.
    The structured rejection reason is stored on
    ``fit_numeric_params.last_reason``.
    """
    fit_numeric_params.last_reason = None  # type: ignore[attr-defined]
    opt, z3_vars, fit_vars, comp, err = _build_optimize(rule_ast, atoms)
    if err is not None:
        fit_numeric_params.last_reason = err  # type: ignore[attr-defined]
        return None

    _, _, _, kwargs = _decompose_rule(rule_ast)
    tolerance_vars = set(kwargs.values())

    if upper_bounds:
        for name, bound in upper_bounds.items():
            if name in z3_vars:
                opt.add(z3_vars[name] <= z3.RealVal(bound))

    # Non-tolerance parameters are minimised by absolute value: introduce
    # an auxiliary |v| variable so the optimiser ranges over magnitudes,
    # not signed reals (which would otherwise drive a free parameter to
    # -inf).
    abs_vars: dict[str, Any] = {}
    objectives: list[tuple[str, Any]] = []
    ordered = sorted(fit_vars, key=lambda v: _tolerance_first_key(v, tolerance_vars))
    for v in ordered:
        z3v = z3_vars[v]
        if v in tolerance_vars:
            objectives.append((v, z3v))
            continue
        abs_v = z3.Real(f"{v.lstrip('?')}__abs")
        opt.add(abs_v >= z3v)
        opt.add(abs_v >= -z3v)
        abs_vars[v] = abs_v
        objectives.append((v, abs_v))

    timeout_ms = _read_timeout_ms()
    opt.set("timeout", timeout_ms)

    # Lex-min: register objectives in priority order. Z3's Optimize
    # interprets sequential minimize() calls as a lexicographic stack
    # under the default :opt.priority lex setting.
    for _, expr in objectives:
        opt.minimize(expr)

    result = opt.check()
    if result == z3.sat:
        model = opt.model()
        out: dict[str, float] = {}
        for v in fit_vars:
            out[v] = _model_value(model, z3_vars[v])
        fit_numeric_params.last_reason = FitReason({  # type: ignore[attr-defined]
            ":phase": ":smt-fit",
            ":reason": ":smt-sat",
            ":values": dict(out),
        })
        return out
    if result == z3.unknown:
        fit_numeric_params.last_reason = FitReason({  # type: ignore[attr-defined]
            ":phase": ":smt-fit",
            ":reason": ":smt-timeout",
            ":timeout-ms": timeout_ms,
        })
        return None
    fit_numeric_params.last_reason = FitReason({  # type: ignore[attr-defined]
        ":phase": ":smt-fit",
        ":reason": ":smt-unsat",
    })
    return None


fit_numeric_params.last_reason = None  # type: ignore[attr-defined]


__all__ = [
    "fit_tolerance",
    "fit_numeric_params",
    "DEFAULT_TIMEOUT_MS",
    "TIMEOUT_ENV_VAR",
    "FitReason",
]
