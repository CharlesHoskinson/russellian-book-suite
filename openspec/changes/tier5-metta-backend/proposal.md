# Change: tier5-metta-backend

**Tier:** 5 of 5 (introduce a 4th codegen backend)
**Branch:** `plan/tier5-metta-runtime`
**Depends on:** Tier 3 (egg-promotion, cozo-runtime), Tier 4 (solver-partitioning)

## Why

Tiers 1-4 left `SUPPORT_MATRIX.md` showing three live backends —
`:z3`, `:egg`, `:cozo` — and the framework presents itself in
documentation and skill prompts as "MeTTa-shaped". An external
analysis comparing this surface to OpenCog's MeTTa /
hyperon-experimental made the diagnosis precise: today's
neurosym-forge is a MeTTa-shaped EDN scaffolder. It imitates
MeTTa idioms (rewrites, multivalued queries, grounded atoms) in
EDN but never links the real hyperon-experimental crate; no
constraint in the framework has ever been discharged by a real
MeTTa interpreter.

A `defconstraint :backend :metta` form does not exist in the
matrix today, and there is no row to flip — the path simply was
never claimed. This change creates it.

## What

- Embed the `hyperon-experimental` Rust crate (`hyperon` on
  crates.io) as a 4th codegen backend in
  `verifiers/*/rust-verifier/src/metta.rs`.
- `defconstraint :backend :metta` routes the constraint's
  `:assert` form into a fresh `&self` MeTTa space and discharges
  it via a `!(match ...)` query against the embedded interpreter.
- The codegen emits a sibling `metta_constraints()` registry next
  to `cozo_constraints()` (Phase I precedent); lib.rs feeds each
  entry through `metta::run_metta`.
- Verdict gains a `:metta-results` field listing each
  `:metta`-backed constraint id and its discharge state.
- A timeout (`VERIFIER_METTA_TIMEOUT_MS`, default 30000) and
  interpreter-error catch keep one bad program from crashing the
  verifier process.
- `SUPPORT_MATRIX.md` gains a new row
  `defconstraint :backend :metta` marked `wired (alpha)` —
  the `(alpha)` qualifier reflects hyperon-experimental's own
  published stability level.
- An integration test exercises a 3-atom MeTTa program (fact +
  rule + query) against the embedded runtime.

## Capabilities touched

- `metta-runtime` — ADD (new capability; hyperon-experimental
  embedded as a 4th codegen backend)

## Implementation notes

See `docs/plans/2026-05-19-tier5-metta-runtime.md`, Phase O.

## Acceptance

- 8 REQ-METTA IDs ship in `specs/metta-runtime/spec.md`.
- `defconstraint :backend :metta` appears in `SUPPORT_MATRIX.md`
  with `wired (alpha)` status; drift lint passes.
- A cargo integration test runs a real `hyperon::Metta` program
  inside the verifier crate and asserts the expected query output.
- `:metta-timeout` and `:metta-error` warnings fire
  deterministically on fixture programs designed to provoke each.
- The existing `:z3`, `:egg`, `:cozo` paths remain unchanged.
