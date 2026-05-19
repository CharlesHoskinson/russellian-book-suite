# Tasks: tier6-smt-numeric-fitting

See `docs/plans/2026-05-19-tier6-theory-induction.md` Phase X for full TDD steps. Task numbers correspond 1:1.

## Phase X.1 — Module skeleton + Z3 binding

- [ ] X1.1: Author `skills/neurosym-forge/scripts/_smt_fit.py` with `fit_tolerance(rule_ast, atoms) -> float | None` and `fit_numeric_params(rule_ast, atoms) -> dict | None` signatures. (REQ-INDUCE-060)
- [ ] X1.2: Wire `z3-solver` Python bindings; `Optimize` API for minimum-ε search with `Abs(lhs - rhs) <= eps` per atom. (REQ-INDUCE-061)

## Phase X.2 — LHS/RHS evaluation helper

- [ ] X2.1: Implement `evaluate_lhs_rhs(rule_ast, atom)` reusing `_canonical.py`'s variable-binding logic to substitute atom values into the rule's LHS/RHS expressions. (REQ-INDUCE-060, REQ-INDUCE-061)

## Phase X.3 — Multi-parameter Pareto fit

- [ ] X3.1: Implement `fit_numeric_params` with multi-objective lex-min via Z3 Optimize; sort key prefers tolerance-flavoured params first, smaller-threshold second. (REQ-INDUCE-062)
- [ ] X3.2: Test multi-parameter fixture: rule with both ε and threshold N; assert tolerance is fit tighter than threshold. (REQ-INDUCE-062)

## Phase X.4 — Timeout handling

- [ ] X4.1: Read `VERIFIER_INDUCTION_FIT_TIMEOUT_MS` (default 10000); pass to Z3 via `opt.set("timeout", ...)`; on `unknown` return `None` with a `{:phase :smt-fit :reason :smt-timeout :timeout-ms <int>}` structured reason; the candidate is DROPPED, NOT retried with looser ε. (REQ-INDUCE-063)
- [ ] X4.2: Timeout fixture: a deliberately complex fit that triggers the bound within 10s; assert `None` returned. (REQ-INDUCE-065)

## Phase X.5 — AST substitution

- [ ] X5.1: After a successful fit, substitute the fitted parameter values into the rule's `:assert` form; the post-fit AST is what flows to downstream validation. (REQ-INDUCE-064)

## Phase X.6 — Tests

- [ ] X6.1: Known-good fixture: 30 synthetic atoms generated from R0 → herd-immunity formula with noise = 0.04; `fit_tolerance` returns ε ≈ 0.05. (REQ-INDUCE-065)
- [ ] X6.2: Impossible fixture: atoms with inconsistent LHS/RHS ratios across documents; `fit_tolerance` returns `None`. (REQ-INDUCE-065)

## Phase X.7 — Commit

- [ ] X7.1: Commit `_smt_fit.py` + tests + fixtures together once X1–X6 are green.
