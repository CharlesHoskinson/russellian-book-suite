# Change: tier6-smt-numeric-fitting

**Tier:** 6 of 7 (theory-induction tier)
**Branch:** `plan/tier6-theory-induction`
**Depends on:** Tier 6 Phase W (candidate-generation)

## Why

A candidate constraint of the shape
`(approx= LHS RHS :tolerance ε)` is structurally complete
but numerically empty until ε is fixed. Asking an LLM to
guess ε is unsound: the proposer has no access to the
atomspace's numeric distribution, so it picks a
plausible-looking constant that frequently fails on the
training atoms or, worse, picks a vacuously loose bound
that satisfies any pair of values. Both deep-research
reports identify this as the NUMSYNTH problem and converge
on the same fix: fit ε via Z3 parameter search against the
atomspace, not via LLM guess.

The same problem applies to threshold parameters in rules
like `(>= :duration N)` — the LLM guesses N; the SMT
fitter finds the minimal N that satisfies the rule on the
training data.

## What

- A new `_smt_fit.py` module exposing
  `fit_tolerance(rule_ast, atoms) -> float | None` and
  `fit_numeric_params(rule_ast, atoms) -> dict | None`.
- Z3 integration via `z3-solver` Python bindings using
  the `Optimize` API for minimum-ε search.
- A Pareto-front discipline for multi-parameter rules
  (tighter tolerance preferred over looser; smaller
  threshold preferred over larger absolute value when
  both fit).
- A `VERIFIER_INDUCTION_FIT_TIMEOUT_MS` env var (default
  10000) bounding each fit; timeouts return `None` with a
  `:smt-timeout` structured reason; the candidate is
  DROPPED, not retried with looser ε.
- A test suite exercising a known-good fixture (herd-
  immunity formula over 30 synthetic atoms), an impossible
  fixture, and a timeout fixture.

## Capabilities touched

- `verifier-build` — EXTEND (adds numeric-fit dispatch
  during the candidate-validation stage of the inducer)

## Implementation notes

See `docs/plans/2026-05-19-tier6-theory-induction.md`,
Phase X.

## Acceptance

- 6 REQ-INDUCE IDs (060–065) ship in
  `specs/verifier-build/spec.md`.
- `fit_tolerance` on the herd-immunity fixture (30 atoms)
  returns ε ≈ 0.05 within 10 seconds.
- An impossible fixture returns `None`; no exception
  propagates to the orchestrator.
- A deliberately complex fixture returns `None` with a
  `:smt-timeout` tag inside `VERIFIER_INDUCTION_FIT_TIMEOUT_MS`.
- Fitted parameters are substituted into the rule's AST
  before the validation stage consumes the rule.
