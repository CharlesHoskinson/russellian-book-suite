# Capability delta: booklogic-dsl — change: booklogic-pr4-active-forms

## ADD

### REQ-DSL-010 — Event-driven

When the BookLogic compiler encounters a `defrule` form, it shall expand
the form to a meander rewrite-rule entry appended to the project's
`rules/rules.edn`.

**Rationale:** Active rules-as-data is the v0.2 → v0.4 migration enabler.
**Tested by:** Per-form CLJS test in `booklogic_test.cljs.tmpl::defrule-expansion` (added in pr4 T1.1, T1.2)

### REQ-DSL-020 — Event-driven

When the BookLogic compiler encounters a `defconstraint` form, it shall
emit an intermediate EDN structure carrying `:backend :z3`, `:assert <expr>`,
`:track <tracker>`, and `:on-unsat <ticket>` slots.

**Rationale:** The Rust codegen consumes this intermediate.
**Tested by:** `booklogic_test.cljs.tmpl::defconstraint-intermediate-shape` (added in pr4 T2.1, T2.2)

### REQ-DSL-021 — Event-driven

When the Python codegen receives the intermediate from REQ-DSL-020, it
shall produce Rust source for `rust-verifier/src/axioms.rs` containing one
`assert_and_track` per constraint with the tracker name as the second
argument.

**Rationale:** The Z3 unsat core surfaces tracker names — that's how
defects map back to constraints.
**Tested by:** `skills/neurosym-forge/tests/test_codegen_axioms.py::test_one_constraint_one_assert_and_track` (added in pr4 T2.3, T2.4)

### REQ-DSL-022 — Optional feature

Where a `defconstraint` carries `~=` (approximate-equality), the codegen
shall desugar to `|lhs - rhs| <= tolerance * |rhs|` for relative
tolerance (the default), or `|lhs - rhs| <= tolerance` if
`:tolerance-kind :absolute` is set.

**Rationale:** Mission OQ #1 — `~=` must support the van 't Hoff 3% case
in osmotic-pressure showcase.
**Tested by:** `skills/neurosym-forge/tests/test_codegen_axioms.py::test_approx_equality_relative` and `::test_approx_equality_absolute` (added in pr4 T2.4)

### REQ-DSL-023 — Ubiquitous

Each `defconstraint` shall contribute one row to a generated
`rules/axioms-tracker-map.edn` mapping the tracker name to
`{:constraint-id ... :claim-id ... :source-span ...}` so an unsat core
can be back-resolved to the BookLogic source line.

**Rationale:** Mission OQ #4 — bidirectional traceability.
**Tested by:** `skills/neurosym-forge/tests/test_codegen_axioms.py::test_tracker_map_emitted` (added in pr4 T2.5, T2.6)

### REQ-DSL-030 — Event-driven

When the BookLogic compiler encounters a `defquery` form, it shall emit
an intermediate EDN structure carrying `:backend :cozo`, `:find <vars>`,
`:where <clauses>`, and `:on-result <ticket>` slots.

**Rationale:** Data-path verification (Cozo) is a peer of solver-path
verification (Z3).
**Tested by:** `booklogic_test.cljs.tmpl::defquery-intermediate-shape` (added in pr4 T3.1, T3.2)

### REQ-DSL-031 — Event-driven

When `kg.rs` runs with one or more compiled `defquery` scripts, it shall
invoke Cozo against the workspace knowledge graph and return a vector of
rows for each script.

**Rationale:** Cozo is the active data backend; the stub `kg.rs` is the
v0.4 gap.
**Tested by:** `skills/neurosym-forge/tests/test_kg_cozo_smoke.py::test_one_query_returns_rows` (added in pr4 T3.4)

### REQ-DSL-040 — Event-driven

When the BookLogic compiler encounters a `defremedy` form, it shall emit
an entry into the project's `rules/remedies.edn` carrying `:when <pattern>`,
`:propose <transition>`, and `:requires <human-review|none>`.

**Rationale:** Remedies feed `book-qa.scripts.propose_writeback.py`.
**Tested by:** `booklogic_test.cljs.tmpl::defremedy-emits-remedies-edn` (added in pr4 T4.1, T4.2)

## MODIFY

(none)

## REMOVE

(none)
