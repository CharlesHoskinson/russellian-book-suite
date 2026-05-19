# Tasks: tier5-cross-chapter

See `docs/plans/2026-05-19-tier5-scale-author.md` Phase R for full
TDD steps. Task numbers track that document.

## Phase R.1 — DSL surface for `:scope :corpus`

- [ ] R1.1: Extend the `defconstraint` reader in
  `skills/neurosym-forge/scripts/_edn_reader.py` (and helpers) to
  accept `:scope :subject` (default) and `:scope :corpus`; reject
  any other value with a clear error. (REQ-CORPUS-050)
- [ ] R1.2: Thread the `:scope` keyword through the constraint
  intermediate representation consumed by `codegen_axioms.py`.

## Phase R.2 — Codegen `axioms_corpus`

- [ ] R2.1: `codegen_axioms.py` emits `pub fn axioms_corpus(solver: &Solver)`
  parallel to Phase J's `axioms_for_subject`; per-subject and
  shared paths remain untouched. (REQ-CORPUS-051)
- [ ] R2.2: Re-vendor the generated lib copy into
  `verifiers/osmotic_pressure/rust-verifier/src/axioms.rs` and
  `verifiers/bermuda/rust-verifier/src/axioms.rs`.

## Phase R.3 — Solver execution order

- [ ] R3.1: `smt::check_all` in both verifiers gains a third stage
  after per-subject + `:shared`: build one fresh `Solver`, assert
  the union of every subject's atoms, call `axioms_corpus`, and
  collect its verdict. (REQ-CORPUS-052)
- [ ] R3.2: Surface the corpus verdict in the top-level merge: any
  `:unsat` from the corpus partition contributes to the top-level
  `:unsat` per Phase J's merge rule.

## Phase R.4 — `:corpus-defects` field

- [ ] R4.1: Verdict structure (`work/verdict.edn`) gains
  `:corpus-defects [{...}]` populated from the corpus partition's
  unsat cores. (REQ-CORPUS-053)
- [ ] R4.2: `verdict_to_qa.py` in both verifiers surfaces
  `:corpus-defects` into the QA JSON output under a parallel
  `corpus_defects` array.

## Phase R.5 — Cozo / `defquery` interop

- [ ] R5.1: When a `:scope :corpus` constraint's body references a
  `defquery` predicate, the framework runs the query over the full
  atom union and applies the constraint to the aggregate; document
  the path in design.md §5. (REQ-CORPUS-054)

## Phase R.6 — Docs + SUPPORT_MATRIX

- [ ] R6.1: `docs/booklogic-dsl-reference.md` §2.5 gains a "Scope"
  subsection documenting `:scope :subject` and `:scope :corpus`,
  with the Mizuno-trial worked example from design.md.
  (REQ-CORPUS-055)
- [ ] R6.2: `skills/neurosym-forge/SUPPORT_MATRIX.md` lists
  `defconstraint :scope :corpus` as `wired`.

## Phase R.7 — Cargo integration test

- [ ] R7.1: `verifiers/osmotic_pressure/rust-verifier/tests/cross_chapter.rs`
  exercises a 2-subject + 1 `:scope :corpus` constraint fixture
  and asserts the verdict identifies the cross-subject conflict.
  (REQ-CORPUS-056)

## Phase R.8 — PR

- [ ] R8.1: Push `plan/tier5-scale-author` (cross-chapter slice) and
  open the PR.
- [ ] R8.2: Merge on green CI.
