# Change: tier1-solver-timeout

**Tier:** 1 of 4
**Branch:** `feat/tier1-solver-timeout`
**Depends on:** none

## Why

The Z3 audit identified a soundness-adjacent gap: `smt::check_all`
calls `solver.check()` with no timeout configured. The current example
verifiers operate in cheap fragments (QF_UFLIA for bermuda; one tiny
QF_NRA instance for osmotic-pressure), so this has never manifested.
But the framework is positioned for arbitrary domains: any future
verifier with nonlinear real arithmetic, mixed theories, or quantifier
instantiations can produce an instance that takes minutes-to-infinity
to decide. With no timeout the verifier process **hangs the entire CI
job indefinitely**, with no recovery path other than the GitHub
Actions step-level timeout — which fails the build with a generic
"the action took too long" rather than the verifier-specific `:unknown`
verdict that downstream consumers know how to interpret.

## What

- Configure a Z3 solver timeout (default 30,000 ms) in `smt::check_all`
  for both existing verifiers and in the scaffold template.
- Read the timeout from the env var `VERIFIER_SOLVER_TIMEOUT_MS` so a
  CI matrix can override per-domain.
- When the timeout fires, Z3 returns `SatResult::Unknown`, which the
  existing `match solver.check()` arm already handles, producing a
  `:unknown` verdict with `solver.get_reason_unknown()` as the
  explanation (typically the string `"timeout"`).
- Add explicit `:unknown` distinguishability at every consumer: the
  pytest smoke harness must distinguish `:unknown` from `:sat` and
  fail rather than treating `:unknown` as success.

## Capabilities touched

- `verifier-build` — MODIFY (adds REQs for solver timeout + `:unknown`
  handling)

## Implementation notes

See `docs/plans/2026-05-18-tier1-general-purpose.md`, Phase B.

## Acceptance

- `smt.rs` in both verifiers calls `Solver::set_param` (or equivalent)
  to set the timeout before `solver.check()`.
- A synthetic hard-NRA constraint fixture returns `:unknown` within
  ~31 seconds, not infinity.
- The scaffold template smt.rs.tmpl inherits the same logic.
- Pytest smoke tests treat `:unknown` as a failure with a distinct
  message (so the operator knows the solver gave up rather than
  reporting `:sat`).
