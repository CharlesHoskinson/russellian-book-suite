"""Tests for skills/neurosym-forge/scripts/_smt_fit.py.

Covers REQ-INDUCE-060..065 (Tier 6 — SMT numeric fitting):

* REQ-INDUCE-060/061: ``fit_tolerance`` finds the minimum ε via Z3
  ``Optimize`` over the training atomspace.
* REQ-INDUCE-062: ``fit_numeric_params`` lex-mins multi-parameter rules
  under the Pareto-front ordering (tolerance before threshold).
* REQ-INDUCE-063: timeout via ``VERIFIER_INDUCTION_FIT_TIMEOUT_MS``;
  ``Z3 == unknown`` returns ``None`` with a structured ``:smt-timeout``
  reason; no retry.
* REQ-INDUCE-064: post-fit values can be substituted into the rule AST
  (orchestrator concern; we test the fitter returns values in a shape
  the orchestrator can consume).
* REQ-INDUCE-065: known-good (sat), impossible (unsat), and timeout
  fixtures all exercised here.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._smt_fit import (  # noqa: E402  (path setup above)
    DEFAULT_TIMEOUT_MS,
    TIMEOUT_ENV_VAR,
    fit_numeric_params,
    fit_tolerance,
)


# ---------------------------------------------------------------------------
# REQ-INDUCE-060, 061, 065(a) — known-good fixture
# ---------------------------------------------------------------------------


def _herd_immunity_atoms(n: int = 30, noise: float = 0.04) -> list[dict]:
    """Synthetic atoms encoding ht = 1 - 1/r0 with bounded noise.

    Atom keys match the rule AST's predicate names (the fitter does no
    name translation — that is the orchestrator's responsibility).
    """
    atoms = []
    for i in range(n):
        r0 = 1.5 + i * 0.1
        ht_exact = 1.0 - 1.0 / r0
        ht_noisy = ht_exact + noise * ((-1) ** i)
        atoms.append({
            "basic-reproduction-number": r0,
            "herd-immunity-threshold": ht_noisy,
        })
    return atoms


def _herd_immunity_rule():
    return (
        "approx=",
        ("herd-immunity-threshold", "?s"),
        ("-", 1.0, ("/", 1.0, ("basic-reproduction-number", "?s"))),
        ":tolerance",
        "?eps",
    )


def test_fit_tolerance_returns_minimum_epsilon_or_none():
    """REQ-INDUCE-060: API returns float | None."""
    eps = fit_tolerance(_herd_immunity_rule(), _herd_immunity_atoms())
    assert eps is None or isinstance(eps, float)


def test_optimize_minimises_epsilon_on_known_good_fixture():
    """REQ-INDUCE-061: Z3 Optimize minimises ε on the herd-immunity atomspace."""
    eps = fit_tolerance(_herd_immunity_rule(), _herd_immunity_atoms())
    assert eps is not None, "expected sat; got None"
    # Noise envelope is 0.04 — ε must be at least that; minimum solution
    # should land in a tight window above the noise floor.
    assert 0.035 <= eps <= 0.06, f"expected ~0.04-0.05, got {eps}"


def test_herd_immunity_fixture_returns_epsilon_005():
    """REQ-INDUCE-065(a): 30 atoms with noise≈0.04 produce ε within ±0.015 of 0.05."""
    start = time.monotonic()
    eps = fit_tolerance(_herd_immunity_rule(), _herd_immunity_atoms())
    elapsed = time.monotonic() - start
    assert eps is not None
    assert 0.035 <= eps <= 0.065, f"want ε~0.05 ± 0.015, got {eps}"
    assert elapsed < 10.0, f"fit took {elapsed:.2f}s; bound is 10s"


# ---------------------------------------------------------------------------
# REQ-INDUCE-065(b) — impossible fixture (unsat path)
# ---------------------------------------------------------------------------


def test_impossible_fixture_returns_none():
    """REQ-INDUCE-065(b): inconsistent ratios with a max_eps cap return None.

    Without ``max_eps`` an ``approx=`` rule is *always* satisfiable by
    a large enough ε; the unsat path is exercised by capping ε. This
    mirrors the orchestrator's job of rejecting vacuously loose fits.
    """
    atoms = [
        {"a": 1.0, "b": 1000.0},  # ratio 1:1000
        {"a": 1.0, "b": 1.0},     # ratio 1:1 — joint ε must cover both
    ]
    rule = (
        "approx=",
        ("a", "?s"),
        ("b", "?s"),
        ":tolerance",
        "?eps",
    )
    eps = fit_tolerance(rule, atoms, max_eps=1.0)
    assert eps is None
    reason = fit_tolerance.last_reason
    assert reason is not None
    assert reason[":reason"] == ":smt-unsat"


def test_unsat_with_missing_predicate_returns_none():
    """Structural failure: predicate absent from atoms → :smt-missing-predicate."""
    atoms = [{"basic-reproduction-number": 1.5}]  # no ht
    eps = fit_tolerance(_herd_immunity_rule(), atoms)
    assert eps is None
    assert fit_tolerance.last_reason[":reason"] == ":smt-missing-predicate"


# ---------------------------------------------------------------------------
# REQ-INDUCE-063, 065(c) — timeout fixture
# ---------------------------------------------------------------------------


def _hard_nra_fixture():
    """A deliberately hard nonlinear-real-arithmetic fit.

    Encodes a high-degree polynomial relationship across many atoms
    with several unknowns coupled through products. Z3's NRA solver
    spends >> 1 second on this, so a 1-ms timeout reliably triggers
    ``unknown``. Returns ``(rule, atoms)``.
    """
    import math
    atoms = []
    for i in range(40):
        x = 0.1 + 0.07 * i
        # The "true" relationship is a 5th-degree polynomial of x
        # convolved with another atom value y. Z3's NRA cannot fit
        # this fast.
        y = math.sin(x * 7.3) + 0.5 * math.cos(x * 13.1)
        z = (x ** 5) - 3 * (x ** 4) * y + 2 * (x ** 3) * (y ** 2) - (x ** 2) * (y ** 3) + 0.7
        atoms.append({"x": x, "y": y, "z": z})
    # The rule fits five coupled coefficients ?a..?e and a tolerance.
    rule = (
        "approx=",
        ("z", "?s"),
        ("+",
            ("*", "?a", ("*", ("x", "?s"), ("*", ("x", "?s"),
                ("*", ("x", "?s"), ("*", ("x", "?s"), ("x", "?s")))))),
            ("*", "?b", ("*", ("x", "?s"), ("*", ("x", "?s"),
                ("*", ("x", "?s"), ("*", ("x", "?s"), ("y", "?s")))))),
            ("*", "?c", ("*", ("x", "?s"), ("*", ("x", "?s"),
                ("*", ("x", "?s"), ("*", ("y", "?s"), ("y", "?s")))))),
            ("*", "?d", ("*", ("x", "?s"), ("*", ("x", "?s"),
                ("*", ("y", "?s"), ("*", ("y", "?s"), ("y", "?s")))))),
            "?e",
        ),
        ":tolerance",
        "?eps",
    )
    return rule, atoms


def test_z3_unknown_drops_candidate_without_retry(monkeypatch):
    """REQ-INDUCE-063: a 1-ms timeout on a hard NRA fit returns None.

    Uses a 5th-degree polynomial fit over 40 atoms with five coupled
    coefficients; Z3's NRA cannot solve this in 1 ms, so ``check()``
    returns ``unknown``. The fitter must propagate that as ``None``
    with a ``:smt-timeout`` reason, NOT retry with a looser ε.
    """
    monkeypatch.setenv(TIMEOUT_ENV_VAR, "1")
    rule, atoms = _hard_nra_fixture()
    eps = fit_tolerance(rule, atoms)
    assert eps is None
    reason = fit_tolerance.last_reason
    assert reason is not None
    assert reason[":reason"] == ":smt-timeout", (
        f"expected :smt-timeout, got {reason!r}"
    )
    assert reason[":timeout-ms"] == 1


def test_timeout_fixture_returns_none_within_bound(monkeypatch):
    """REQ-INDUCE-065(c): timeout returns None within the wall-clock bound."""
    monkeypatch.setenv(TIMEOUT_ENV_VAR, "1")
    rule, atoms = _hard_nra_fixture()
    start = time.monotonic()
    eps = fit_tolerance(rule, atoms)
    elapsed = time.monotonic() - start
    assert eps is None
    # Bound is the *default* 10s; the timeout-triggered path must exit
    # well inside that envelope.
    assert elapsed < 5.0, f"timeout fit took {elapsed:.2f}s; bound is 5s"


def test_timeout_env_default_when_unset(monkeypatch):
    """``VERIFIER_INDUCTION_FIT_TIMEOUT_MS`` unset → 10000 ms."""
    monkeypatch.delenv(TIMEOUT_ENV_VAR, raising=False)
    # Sat path completes; we just confirm no exception and the API
    # returns a usable float.
    eps = fit_tolerance(_herd_immunity_rule(), _herd_immunity_atoms())
    assert eps is not None
    assert DEFAULT_TIMEOUT_MS == 10_000


def test_timeout_env_bogus_falls_back_to_default(monkeypatch):
    """Non-integer ``VERIFIER_INDUCTION_FIT_TIMEOUT_MS`` reverts to default."""
    monkeypatch.setenv(TIMEOUT_ENV_VAR, "not-a-number")
    eps = fit_tolerance(_herd_immunity_rule(), _herd_immunity_atoms())
    assert eps is not None  # sat under default 10s budget


# ---------------------------------------------------------------------------
# REQ-INDUCE-062 — multi-param Pareto-front fitting
# ---------------------------------------------------------------------------


def test_multi_parameter_pareto_prefers_tolerance_then_threshold():
    """REQ-INDUCE-062: ``(approx= (- (:x ?s) ?N) 0 :tolerance ?eps)``

    encodes a rule that needs *both* a centre N and a tolerance ε. The
    Pareto-front ordering minimises ε first (priority 1), then |N|.
    With atoms clustered around 5.0 ± 0.1, the fitted ε should be ≈0.1
    and the fitted N should be ≈5.0.
    """
    atoms = [{"x": 5.0 + 0.1 * ((-1) ** i)} for i in range(20)]
    rule = (
        "approx=",
        ("-", ("x", "?s"), "?N"),
        0.0,
        ":tolerance",
        "?eps",
    )
    out = fit_numeric_params(rule, atoms)
    assert out is not None
    assert "?eps" in out and "?N" in out
    eps = out["?eps"]
    n = out["?N"]
    assert 0.05 <= eps <= 0.15, f"want ε~0.1, got {eps}"
    assert 4.5 <= n <= 5.5, f"want N~5.0, got {n}"


def test_multi_parameter_handles_unsat(monkeypatch):
    """Multi-param fitter returns None on inconsistent atoms under bound."""
    atoms = [{"x": 1.0}, {"x": 1000.0}]
    rule = (
        "approx=",
        ("-", ("x", "?s"), "?N"),
        0.0,
        ":tolerance",
        "?eps",
    )
    out = fit_numeric_params(rule, atoms, upper_bounds={"?eps": 1.0})
    assert out is None
    assert fit_numeric_params.last_reason[":reason"] == ":smt-unsat"


def test_multi_parameter_timeout(monkeypatch):
    """Multi-param fitter propagates timeout the same way as the single-param API."""
    monkeypatch.setenv(TIMEOUT_ENV_VAR, "1")
    atoms = [{"x": 5.0 + 0.01 * i} for i in range(50)]
    rule = (
        "approx=",
        ("-", ("x", "?s"), "?N"),
        0.0,
        ":tolerance",
        "?eps",
    )
    out = fit_numeric_params(rule, atoms)
    if out is None:
        assert fit_numeric_params.last_reason[":reason"] == ":smt-timeout"
        assert fit_numeric_params.last_reason[":timeout-ms"] == 1
    # On very fast machines Z3 may still finish within 1ms — only assert
    # the timeout-reason path when timeout actually fires. The strict
    # timeout-propagation contract is covered by
    # ``test_z3_unknown_drops_candidate_without_retry`` above.


# ---------------------------------------------------------------------------
# REQ-INDUCE-064 — post-fit values are substitution-ready
# ---------------------------------------------------------------------------


def test_post_fit_ast_has_fitted_values_substituted():
    """The fitter returns a float in a form the orchestrator can drop into
    the rule AST verbatim (no Z3 sentinel types leak out)."""
    eps = fit_tolerance(_herd_immunity_rule(), _herd_immunity_atoms())
    assert isinstance(eps, float)
    assert eps == eps  # not NaN

    # Smoke-test substitution: replacing "?eps" yields a tuple with
    # only str / int / float leaves.
    original = _herd_immunity_rule()

    def substitute(node):
        if node == "?eps":
            return eps
        if isinstance(node, tuple):
            return tuple(substitute(c) for c in node)
        return node

    substituted = substitute(original)

    def leaves_ok(node) -> bool:
        if isinstance(node, tuple):
            return all(leaves_ok(c) for c in node)
        return isinstance(node, (str, int, float))

    assert leaves_ok(substituted)
    # And ?eps no longer appears.
    flat = repr(substituted)
    assert "?eps" not in flat
