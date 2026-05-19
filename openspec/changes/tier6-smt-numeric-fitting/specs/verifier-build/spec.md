# Capability delta: verifier-build — change: tier6-smt-numeric-fitting

This change extends `verifier-build` with an SMT-based
numeric parameter fitter for candidate constraints
produced by the Tier 6 inducer. Where a candidate carries
a `:tolerance` ε or threshold parameter, the fitter calls
Z3's `Optimize` to find the minimum value that satisfies
the rule across the training atomspace; LLM-guessed
numerics are replaced by exact SMT-fit values. The post-fit
rule is what flows to downstream validation.

## ADD

### REQ-INDUCE-060 — Ubiquitous

The framework SHALL ship
`skills/neurosym-forge/scripts/_smt_fit.py` exposing
`fit_tolerance(rule_ast, atoms) -> float | None` that
returns the minimum tolerance ε for which the rule's
`approx=` form holds across all bound atoms, or `None` if
no finite ε works.

**Rationale:** A central, importable fitter lets the
orchestrator (and future phases) call into one numeric-fit
implementation rather than re-implementing per-call. The
`float | None` return type makes the failure case
mechanical at the call site.
**Tested by:** `tests/test_smt_fit.py::test_fit_tolerance_returns_minimum_epsilon_or_none` (added in X1.1).

### REQ-INDUCE-061 — Ubiquitous

The fitter SHALL invoke Z3 via the `z3-solver` Python
bindings; the existential search SHALL use the `Optimize`
API to minimise ε subject to the rule holding on all bound
atom values (`Abs(lhs(atom) - rhs(atom)) <= eps` for each
atom in the training set).

**Rationale:** `Optimize` is Z3's native multi-objective
solver; it handles minimum-ε search and lex-min ordering
in a single check. Encoding the rule as a per-atom
conjunction avoids quantifier elimination issues when the
training set is small and concrete.
**Tested by:** `tests/test_smt_fit.py::test_optimize_minimises_epsilon_on_known_good_fixture` (added in X1.2).

### REQ-INDUCE-062 — Optional feature

WHERE the rule has multiple numeric parameters (e.g.,
`(>= (:x ?d) N)` with N to fit jointly with a tolerance
ε), `fit_numeric_params(rule_ast, atoms)` SHALL return a
dict `{param-name: value}` minimising the rule's
complexity under a Pareto-front ordering: tighter
tolerance preferred over looser; smaller threshold
preferred over larger absolute value when both fit.

**Rationale:** Real candidates carry more than one numeric
parameter; a univariate ε fitter would force the
orchestrator to glue together multiple fit calls and pick a
priority order by hand. The Pareto-front ordering names the
priority explicitly so the fitter's behaviour is
predictable.
**Tested by:** `tests/test_smt_fit.py::test_multi_parameter_pareto_prefers_tolerance_then_threshold` (added in X3.2).

### REQ-INDUCE-063 — Unwanted behaviour

IF Z3 returns `unknown` (timeout or undecidable) within
`VERIFIER_INDUCTION_FIT_TIMEOUT_MS` (default 10000), the
fitter SHALL return `None` with a structured
`{:phase :smt-fit :reason :smt-timeout
:timeout-ms <int>}` reason attached to the candidate's
post-mortem record; the candidate SHALL be DROPPED, NOT
retried with a looser ε.

**Rationale:** Retrying with looser ε would silently
weaken the induced theory. A candidate Z3 cannot fit
inside the bound is not worth keeping. Drop-on-timeout
preserves the theory's soundness; the bound is the safety
net, not a knob to relax under pressure.
**Tested by:** `tests/test_smt_fit.py::test_z3_unknown_drops_candidate_without_retry` (added in X4.1, X4.2).

### REQ-INDUCE-064 — Ubiquitous

Fitted parameter values SHALL be substituted into the
rule's `:assert` AST BEFORE downstream validation
consumes the rule; the post-fit form (with concrete
numbers in place of fit variables) is what reaches the
validation stage.

**Rationale:** Downstream validation runs unchanged
verifier code; that code expects concrete numeric
literals. Substituting at the fitter boundary keeps the
validation surface free of fit-variable concerns and
makes the fit step a pure transformation on the rule AST.
**Tested by:** `tests/test_smt_fit.py::test_post_fit_ast_has_fitted_values_substituted` (added in X5.1).

### REQ-INDUCE-065 — Ubiquitous

A test suite SHALL exercise: (a) a known-good fixture in
which 30 synthetic atoms encode the R0 → herd-immunity
formula with noise ≈ 0.04 and `fit_tolerance` returns ε
within ±0.01 of 0.05; (b) an impossible fixture in which
LHS / RHS ratios are inconsistent across documents and
`fit_tolerance` returns `None` (unsat path); (c) a
timeout fixture in which a deliberately complex fit
triggers the `VERIFIER_INDUCTION_FIT_TIMEOUT_MS` bound and
returns `None` within 10s wall-clock.

**Rationale:** Three orthogonal fixtures cover the three
result paths (sat / unsat / unknown). Without all three
the fitter's failure modes degrade silently as Z3 versions
shift.
**Tested by:** `tests/test_smt_fit.py::{test_herd_immunity_fixture_returns_epsilon_005,test_impossible_fixture_returns_none,test_timeout_fixture_returns_none_within_bound}` (added in X6.1, X6.2, X4.2).
