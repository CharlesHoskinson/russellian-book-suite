# Design: booklogic-pr6-osmotic-showcase

## Architecture pointer

Full TDD-shaped detail at `docs/plans/2026-05-17-booklogic-pr6.md`.

## Dependencies

- PR-4 must have shipped `defconstraint` + `axioms.rs` codegen + the
  `~=` operator (with the mission spec's relative-tolerance semantics).
- PR-5 must have established the `ubuntu-latest` Z3 CI build path; PR-6
  follows the same approach.

## Verdict-shape note

The current `verifiers/bermuda/rust-verifier/src/ir.rs::emit_verdict`
writes `:status`; PR-4's revamped emitter writes `:verdict`. The PR-6
smoke harness accepts both keys to avoid coupling to a specific emit
order.

## Open questions

None.
