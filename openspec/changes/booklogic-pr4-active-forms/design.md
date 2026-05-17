# Design: booklogic-pr4-active-forms

## Architecture pointer

Full TDD-shaped detail at `docs/plans/2026-05-17-booklogic-pr4.md`.

## Pre-declared a/b split

Decision point: after Phase 2 acceptance (defconstraint codegen + `cargo check`
gate green). Split into PR-4a + PR-4b if **any** of:

1. `cargo check --features kg` fails with a Cozo dependency error that
   doesn't resolve in a focused investigation block.
2. Cozo dyn-link API differs from documented `cozo = "0.7"` in a way that
   requires upstream patching.
3. Track A is fully green and the executor needs to ship before Track B
   is testable.

Otherwise: one PR-4.

## Open-question resolution

- OQ #1 (`~=` operator): in scope, Phase 2.3 `_emit_approx_block`.
- OQ #4 (bidirectional traceability): solved via generated
  `rules/axioms-tracker-map.edn` (keyed by tracker name).
- OQ #5 (Z3 bundled on Windows): deferred to PR-5; PR-4 uses `cargo check`
  not `cargo build` so the C++ link is skipped.

## Cargo manifest path

`<project>/rust-verifier/Cargo.toml` (template-instantiated).
