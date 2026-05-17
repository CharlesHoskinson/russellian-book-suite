# Change: booklogic-pr4-active-forms

**Sprint:** 3 of 5
**Branch:** `feat/booklogic-pr4`
**GitHub Milestone:** `booklogic-pr4-active-forms`

## Why

The BookLogic compiler shipped `defsort`, `defpredicate`, `deflift` in
PR-3 — the passive declarative forms. The four active forms (`defrule`,
`defconstraint`, `defquery`, `defremedy`) are absent. Without them,
Bermuda cannot be migrated off the hand-coded `canonical.rs` + Cozo stub
+ ad-hoc writeback.

## What

- Extend `booklogic.cljs.tmpl` with the four expanders.
- Codegen `rust-verifier/src/axioms.rs` from `defconstraint`.
- Wire real Cozo into `kg.rs` as the `defquery` backend.
- Teach `book-qa.scripts.propose_writeback.py` to accept BookLogic remedies.
- Per-form compiler tests + axioms shape tests + Cozo query smoke +
  remedy adapter test.

## Pre-declared split

This is the long pole. The change is structured as two tracks:

- **Track A:** Phases 1, 2 (defrule + defconstraint + axioms codegen). Pure Z3.
- **Track B:** Phases 3, 4 (defquery + Cozo + defremedy + writeback).

Decision point after Phase 2 acceptance. If Cozo build is non-trivial
or executor needs to ship before Track B is testable, split into
`booklogic-pr4a-defconstraint` and `booklogic-pr4b-defquery-defremedy`.
The split criteria are documented in `design.md`.

## Capabilities touched

- `booklogic-dsl` — ADD requirements for the four active forms
- `qa-defect-pipeline` — ADD requirement for BookLogic remedy acceptance
- `verifier-build` — ADD requirement for axioms.rs codegen + cargo check gate

## Implementation notes

See `docs/plans/2026-05-17-booklogic-pr4.md` — long, 7 phases, including the
pre-declared a/b split.

## Acceptance

- All four expanders have passing compiler tests
- `axioms.rs` generated from a sample project passes `cargo check`
- `kg.rs` Cozo path returns expected rows for one fixture query
- `propose_writeback` emits a remedy-driven transition for a fixture verdict
- Mission spec § D4 footer updated
- All REQ IDs added are test-covered
