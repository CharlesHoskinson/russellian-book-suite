# Capability delta: verifier-build — change: tier1-solver-timeout

## ADD

### REQ-VERIFIER-BUILD-040 — Ubiquitous

The `smt::check_all` function in every verifier's `rust-verifier/src/smt.rs`
SHALL configure the Z3 solver with a wall-clock timeout via
`solver.set_params(&Params)` BEFORE invoking `solver.check()`.

**Rationale:** Without a timeout, any Z3 instance the solver cannot
decide in bounded time (undecidable theories, hard QF_NRA, quantifier
instantiation loops) hangs the verifier process indefinitely. The
timeout makes the worst-case bounded.
**Tested by:** `verifiers/osmotic_pressure/rust-verifier/src/smt.rs::tests::hard_nra_returns_unknown_within_timeout` (added in B1.1)

### REQ-VERIFIER-BUILD-041 — Optional feature

WHERE the env var `VERIFIER_SOLVER_TIMEOUT_MS` is set to a positive
integer N, the verifier SHALL use N milliseconds as the Z3 solver
timeout in place of the default 30,000 ms.

**Rationale:** A CI matrix that wants to budget a known-slow domain at
5 minutes can set `VERIFIER_SOLVER_TIMEOUT_MS=300000`; a fast smoke
run can set 5000. Per-domain calibration without recompilation.
**Tested by:** `smt::tests::env_var_overrides_default_timeout` (added in B2.1)

### REQ-VERIFIER-BUILD-042 — Event-driven

WHEN `smt::check_all` returns a `Verdict` with `status = "unknown"`,
the pytest smoke harness for that verifier SHALL fail the test with
an explicit message distinguishing solver-timeout / solver-incompleteness
from a `:sat`/`:unsat` expectation mismatch.

**Rationale:** A `:unknown` verdict means the solver could not decide;
treating it as `:sat` produces silent false positives, treating it as
`:unsat` produces silent false negatives. The smoke must surface the
distinction so the operator knows to either raise the timeout, fix the
constraint, or accept the indeterminacy.
**Tested by:** `tests/test_smoke.py::test_unknown_verdict_fails_with_distinguished_message` (added in B4.1)

### REQ-VERIFIER-BUILD-043 — Ubiquitous

The neurosym-forge scaffold template `smt.rs.tmpl` SHALL include the
same `VERIFIER_SOLVER_TIMEOUT_MS`-aware timeout configuration as the
existing per-verifier `smt.rs` files, so every newly scaffolded project
inherits the bound by construction.

**Rationale:** Every future verifier inherits the gate by default;
no domain author can accidentally ship a verifier without the bound.
**Tested by:** `skills/neurosym-forge/tests/test_scaffold_bake.py::test_baked_smt_rs_has_timeout_config` (added in B5.2)
