# Capability delta: booklogic-dsl — change: tier5-cross-chapter

## ADD

### REQ-CORPUS-050 — Ubiquitous

The `defconstraint` form SHALL accept an optional `:scope` key whose
value is either `:subject` (default) or `:corpus`. When `:scope` is
omitted, the constraint SHALL behave identically to the existing
Phase J per-subject path. Any value of `:scope` other than `:subject`
or `:corpus` SHALL be rejected at ingest time with an error naming
the offending constraint id.

**Rationale:** Authors need a surface to opt into corpus-scope
checking; defaulting to `:subject` keeps every existing constraint
intact and makes the new behaviour explicit at the call site.
**Tested by:**
`skills/neurosym-forge/tests/test_codegen_axioms.py::test_scope_corpus_accepted_and_threaded`
(added in R1.1)

### REQ-CORPUS-051 — Optional feature

WHERE a `defconstraint` declares `:scope :corpus`, the codegen
SHALL emit a `pub fn axioms_corpus(solver: &Solver)` accessor in
the generated `axioms.rs` module, parallel to Phase J's
`axioms_for_subject`. The per-partition `smt::check_all` SHALL run
the corpus-scope axioms once over the union of every subject's
atoms, after all per-subject partitions and the Phase J `:shared`
partition complete.

**Rationale:** Mirroring Phase J's accessor shape keeps the
generated module readable and lets the executor compose the
per-subject and corpus paths without special-casing.
**Tested by:**
`verifiers/osmotic_pressure/rust-verifier/src/smt.rs::tests::corpus_axioms_run_over_union`
(added in R3.1)

### REQ-CORPUS-052 — Unwanted behaviour

IF a `:scope :corpus` constraint references a predicate also bound
at per-subject scope (e.g.,
`(approx= (:trial-n ?t1) (:trial-n ?t2) 0.0)`), THEN Z3's view in
the corpus partition SHALL see both subjects' bindings
simultaneously, and the partitioning SHALL preserve union access
for corpus-scope axioms — the constraint MUST NOT silently see
only one subject's atoms.

**Rationale:** A cross-chapter consistency rule that ran against a
single subject's slice would silently pass; the executor has to
seed the corpus solver with every subject's atoms for the
constraint to mean what the author wrote.
**Tested by:**
`verifiers/osmotic_pressure/rust-verifier/tests/cross_chapter.rs::corpus_sees_all_subject_bindings`
(added in R7.1)

### REQ-CORPUS-053 — Ubiquitous

The verdict surface SHALL gain a `:corpus-defects` field listing
every `:scope :corpus` constraint that returned `:unsat`. Each
entry SHALL be a map of the shape
`{:constraint-id ... :defect-id ... :subjects [...] :explanation ...}`
naming the constraint, the declared `:on-unsat` defect id, the
subjects whose atoms participated in the unsat core, and a
human-readable explanation of the conflict.

**Rationale:** Operators need to distinguish a per-subject defect
(Phase J's `:unsat-core`) from a cross-corpus defect; surfacing
the subject names is what makes a "trial-n disagrees" failure
actionable rather than mystifying.
**Tested by:**
`verifiers/osmotic_pressure/rust-verifier/tests/cross_chapter.rs::corpus_defects_field_names_subjects`
(added in R4.1)

### REQ-CORPUS-054 — Optional feature

WHERE a `:scope :corpus` constraint's body references a `defquery`
predicate (Phase I's Cozo path), the framework SHALL run the query
over the full atom union (every subject's atoms together) and
apply the constraint to the aggregate result rows rather than
running the query per-subject and unioning the verdicts.

**Rationale:** A query that says "find every trial cited more than
once" only makes sense at corpus scope; running it per-subject
would always return empty rows because each subject sees its own
slice.
**Tested by:**
`verifiers/osmotic_pressure/rust-verifier/tests/cross_chapter.rs::corpus_scope_query_aggregates_subjects`
(added in R5.1)

### REQ-CORPUS-055 — Ubiquitous

`docs/booklogic-dsl-reference.md` §2.5 SHALL grow a "Scope"
subsection documenting `:scope :subject` (default) and
`:scope :corpus`, including the Mizuno-trial worked example.
`skills/neurosym-forge/SUPPORT_MATRIX.md` SHALL gain a
`defconstraint :scope :corpus` row marked `wired`.

**Rationale:** A new DSL surface that's undocumented is
indistinguishable from a bug; the author-facing reference and the
support matrix are the canonical surfaces authors consult.
**Tested by:**
`tests/test_dsl_reference.py::test_scope_subsection_present`
(added in R6.1)

### REQ-CORPUS-056 — Ubiquitous

A cargo integration test SHALL exercise a 2-subject corpus + 1
cross-subject `:scope :corpus` constraint fixture in which the two
subjects record disagreeing values for the same logical entity
(e.g., trial-n = 37 in subject A, trial-n = 42 in subject B). The
test SHALL assert that the verdict's top-level status is `:unsat`,
that `:corpus-defects` contains exactly one entry, and that the
entry's `:subjects` field names both subjects.

**Rationale:** The end-to-end fixture is what proves the codegen,
the execution order, and the verdict shape all line up; unit
tests on individual stages can pass while the integration silently
fails.
**Tested by:**
`verifiers/osmotic_pressure/rust-verifier/tests/cross_chapter.rs::two_subject_disagreement_surfaces_corpus_defect`
(added in R7.1)
