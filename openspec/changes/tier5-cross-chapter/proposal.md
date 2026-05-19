# Change: tier5-cross-chapter

**Tier:** 5 of 5 (scale + author-facing tier)
**Branch:** `plan/tier5-scale-author`
**Depends on:** `tier4-solver-partitioning`

## Why

Phase J partitions atoms by `:subject` and runs one Z3 solver per
subject. That's correct for the common case — each subject's atoms
describe one entity in the domain — but it forecloses cross-chapter
consistency. The ADSC report cites the same Mizuno 2008 trial in two
chapters, once recording `n=37, p=0.001` and once recording
`n=42, p=0.001` after a copy-paste drift; the framework today cannot
catch the disagreement because each chapter's atoms partition into a
separate solver instance and never meet.

The existing `defconstraint` form has no surface for "this rule walks
the whole corpus." Authors need it for trial-data consistency, for
cross-chapter unit consistency, and for any obligation that says "the
same fact, cited twice, must agree." Without it, the framework rates
single chapters cleanly while missing the structural defects that
matter most to readers.

## What

- Add `:scope :corpus` modifier to `defconstraint` (default
  `:scope :subject` preserves Phase J's per-subject behaviour).
- Codegen emits an `axioms_corpus(solver)` accessor parallel to
  Phase J's `axioms_for_subject`.
- `smt::check_all` runs corpus-scope axioms once over the union of
  all subjects' atoms, after the per-subject partitions complete.
- The verdict surface grows `:corpus-defects` listing every
  `:scope :corpus` constraint that failed and naming the conflicting
  subjects in the explanation.
- DSL reference §2.5 grows a "Scope" subsection; SUPPORT_MATRIX.md
  documents the modifier.

## Capabilities touched

- `booklogic-dsl` — EXTEND (adds REQ-CORPUS-050..056)

## Implementation notes

See `docs/plans/2026-05-19-tier5-scale-author.md`, Phase R.

## Acceptance

- 7 REQ-CORPUS IDs ship in `specs/booklogic-dsl/spec.md`.
- A 2-subject + 1 cross-subject corpus-scope fixture compiles via
  `make ci` and the verdict's `:corpus-defects` field correctly
  identifies the cross-subject conflict.
- DSL reference §2.5 documents `:scope :subject` and `:scope :corpus`.
- SUPPORT_MATRIX.md gains a `defconstraint :scope :corpus` row.
