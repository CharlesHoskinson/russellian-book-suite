"""Tests for skills/neurosym-forge/scripts/_smt_fit.py.

Initial slice — REQ-INDUCE-060, 061, 065 (a, b):

* REQ-INDUCE-060: ``fit_tolerance`` exists with the documented signature.
* REQ-INDUCE-061: Z3 ``Optimize`` finds the minimum ε across the
  training atomspace.
* REQ-INDUCE-065(a): known-good fixture (herd-immunity formula across
  30 synthetic atoms with noise ≈ 0.04) returns ε within ±0.015 of 0.05.
* REQ-INDUCE-065(b): impossible fixture returns ``None``.

Timeout handling (REQ-INDUCE-063) and multi-param Pareto fitting
(REQ-INDUCE-062) ship in subsequent commits and add their own cases.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._smt_fit import fit_tolerance  # noqa: E402


def _herd_immunity_atoms(n: int = 30, noise: float = 0.04) -> list[dict]:
    """Synthetic atoms encoding ht = 1 - 1/r0 with bounded noise.

    Atom keys match the rule AST's predicate names — the fitter does no
    name translation, that is the orchestrator's responsibility.
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
    # Noise envelope is 0.04; minimum solution lands tightly above it.
    assert 0.035 <= eps <= 0.06, f"expected ~0.04-0.05, got {eps}"


def test_herd_immunity_fixture_returns_epsilon_005():
    """REQ-INDUCE-065(a): 30 atoms with noise≈0.04 produce ε within ±0.015 of 0.05."""
    start = time.monotonic()
    eps = fit_tolerance(_herd_immunity_rule(), _herd_immunity_atoms())
    elapsed = time.monotonic() - start
    assert eps is not None
    assert 0.035 <= eps <= 0.065, f"want ε~0.05 ± 0.015, got {eps}"
    assert elapsed < 10.0, f"fit took {elapsed:.2f}s; bound is 10s"


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


def test_post_fit_value_is_substitution_ready():
    """REQ-INDUCE-064: the fitter returns a float that drops cleanly
    into the rule AST in place of the ?eps placeholder."""
    eps = fit_tolerance(_herd_immunity_rule(), _herd_immunity_atoms())
    assert isinstance(eps, float)
    assert eps == eps  # not NaN

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
    assert "?eps" not in repr(substituted)
