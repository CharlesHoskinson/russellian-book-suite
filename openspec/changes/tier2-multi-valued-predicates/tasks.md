# Tasks: tier2-multi-valued-predicates

See `docs/plans/2026-05-18-tier234-and-usefulness.md` Phase E.3 for full
TDD steps. Task numbers correspond 1:1.

> **Note:** REQ-IDs are REQ-DSL-050..055 (not 040..045) — see design.md
> for the collision-avoidance rationale against the unmerged
> `booklogic-pr4-active-forms` REQ-DSL-040.

## Phase E.3.1 — Grammar acceptance in `defpredicate`

- [ ] E3.1.1: Failing test `skills/neurosym-forge/tests/test_defpredicate_grammar.py::test_vector_return_sort_accepted`. (REQ-DSL-050)
- [ ] E3.1.2: Extend `expand-predicates` in `booklogic.cljs.tmpl` to accept `[:vector <sort>]` and `[:set <sort>]` as return shape. (REQ-DSL-050)
- [ ] E3.1.3: Failing test `test_set_return_sort_accepted`. (REQ-DSL-050)

## Phase E.3.2 — Codegen Z3 lowering

- [ ] E3.2.1: Failing test `skills/neurosym-forge/scripts/tests/test_codegen_axioms_collections.py::test_vector_predicate_lowers_to_array`. (REQ-DSL-051)
- [ ] E3.2.2: Extend `_emit_expr_typed` to produce `Array::new_const("<var-name>", Int, <inner>)` for vector returns + paired `Int::new_const("<var-name>_len")`. (REQ-DSL-051)
- [ ] E3.2.3: Failing test `test_set_predicate_lowers_to_z3_set`. (REQ-DSL-052)
- [ ] E3.2.4: Extend `_emit_expr_typed` to produce `Set::new_const("<var-name>", <inner>)` for set returns. (REQ-DSL-052)

## Phase E.3.3 — Aggregate operators

- [ ] E3.3.1: Failing test `test_sum_aggregate_emits_array_fold`. (REQ-DSL-053)
- [ ] E3.3.2: Extend `_emit_z3_block` dispatch with `sum`, `count`, `in`, and `forall...in...`. (REQ-DSL-053)

## Phase E.3.4 — Strict binding on type mismatch

- [ ] E3.4.1: Failing Rust unit test `verifiers/osmotic_pressure/rust-verifier/tests/multi_valued_binding.rs::scalar_value_for_set_predicate_errors`. (REQ-DSL-054)
- [ ] E3.4.2: Extend `smt::check_all`'s value-dispatch arm to consult `booklogic-schema.edn` for the declared return shape and raise `Error::Smt` on scalar-vs-container mismatch. (REQ-DSL-054)

## Phase E.3.5 — Schema-file encoding

- [ ] E3.5.1: Failing test `test_schema_emits_vector_set_return_shapes`. (REQ-DSL-055)
- [ ] E3.5.2: Update the CLJS `emit-schema-edn` writer to round-trip the new return shape. (REQ-DSL-055)
- [ ] E3.5.3: Update the Python schema reader in `ingest_ledger.py` to accept the new shape and pass the declared shape through to the emitted atom.

## Phase E.3.6 — DSL reference + commit

- [ ] E3.6.1: Update `docs/booklogic-dsl-reference.md` § 2.2 to document the extended return-sort grammar.
- [ ] E3.6.2: Update § 2.5 to document `sum`, `count`, `in`, `forall...in...` aggregates.
- [ ] E3.6.3: Commit `openspec(tier2): multi-valued predicates change folder (REQ-DSL-050..055)` once specs land.
