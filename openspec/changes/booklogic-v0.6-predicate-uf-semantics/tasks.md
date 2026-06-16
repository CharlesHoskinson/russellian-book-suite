# Tasks: booklogic-v0.6-predicate-uf-semantics

Detailed design in `design.md`. Each task is TDD-shaped: failing test citing the
REQ-ID → minimal impl → green → commit. One problem per PR. No AI attribution.
Run the suite via `cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest
tests -q`. Verify Rust via CI (`cargo check --features smt`), not locally.

> **Status 2026-06-16.** Implemented on `feat/booklogic-v0.6-predicate-uf`
> (commits `5deab50` codegen+tests, `380d83e` docs+golden). Unit layer complete:
> 13 tests in `test_codegen_axioms_predicate_uf.py`, full codegen+matrix suite 76
> green. Remaining items are CI-verified (cargo) or explicitly deferred — see below.

## Phase A — OpenSpec record

- [x] Task 0: OpenSpec record + branch `feat/booklogic-v0.6-predicate-uf` (this change)

## Phase B — Predicate-UF registry

- [x] REQ-SMT-056 — Task 1: `_PREDICATE_UFS` registry in `generate_axioms_source`;
      nil/empty `:arg-sorts` excluded (`test_nil_arity_predicate_keeps_opaque_bool`).
- [x] REQ-SMT-056 — Task 1b: `_is_bool_sort` + `_sort_ref_expr` helpers (primitive →
      `Sort::int()/real()/bool()/string()`, custom → `<sort>_sort` uninterpreted const).

## Phase C — FuncDecl preamble + plumbing

- [x] REQ-SMT-057 — Task 2: `_PREDICATE_UFS` module global consumed by
      `_emit_bool_subexpr` / `_emit_quantifier_expr`; one `FuncDecl::new(...)` per
      block (`test_funcdecl_declared_once_per_block`, `test_funcdecl_range_is_bool`).

## Phase D — Application emission + validation

- [x] REQ-SMT-058 — Task 3: keyword arm emits `<pred>_fn.apply(...).as_bool().unwrap()`
      (`test_predicate_in_forall_emits_apply`, `test_no_opaque_bool_for_registered_predicate`).
- [~] REQ-SMT-059 — Task 4: **arity** validation done (`test_arity_mismatch_raises`).
      Per-position **arg-sort** validation deferred (needs threading bound-var sorts);
      tracked as a follow-up — see note below.
- [x] REQ-SMT-058 — Task 4b: `_resolve_pred_arg` — `?var`→bound const, unbound raises,
      ground keyword → sort-typed const (`test_unbound_variable_raises`,
      `test_ground_arg_resolves_to_sorted_const`).

## Phase E — Backward-compat / determinism pin

- [x] REQ-SMT-061 — Task 5 (unit): nil-arity predicates keep the opaque path.
- [ ] REQ-SMT-061 — Task 5b (CI): regenerate `axioms.rs` for bermuda +
      osmotic_pressure and assert byte-identical to baseline (no local cargo).

## Phase F — Soundness proof

- [x] REQ-SMT-060 — Task 6 (unit): `test_soundness_shape_exposes_opaque_collision`
      pins that `(forall [?a] (:p ?a))` + `(exists [?b] (not (:p ?b)))` both apply the
      same FuncDecl (distinct opaque Bools under v0.5 — the bug).
- [ ] REQ-SMT-060 — Task 6b (CI `--features smt`): entailed → `:unsat`,
      non-entailed → `:sat` on a real verifier build.

## Phase G — Docs + golden fixture

- [x] REQ-BOOKLOGIC-054 — Task 7: SUPPORT_MATRIX row **wired (v0.6)**; caveat section
      rewritten to the UF semantics; `TODO(Tier 3)` removed (`test_no_tier3_todo_remains`,
      `test_support_matrix_quantifier_row_is_wired`).
- [x] REQ-BOOKLOGIC-055 — Task 8: DSL reference §2.8/§2.9/§2.10 added
      (`test_dsl_reference_documents_operators`).
- [x] REQ-BOOKLOGIC-056 — Task 9: `tests/golden/predicate_uf_v0_6.edn` + golden test.

## Phase H — End-to-end + PR

- [ ] REQ-SMT-061 — Task 10: `cargo check --features smt` green for osmotic_pressure
      and bermuda on CI (no local cargo).
- [ ] Task 11: Push + open PR.

## Follow-up

- **Per-position arg-sort validation (REQ-SMT-059 remainder):** verify each
  predicate argument's sort against the schema, not just arity. Requires threading
  bound-variable sorts through `bound_vars` (today it maps name→const only). Small,
  isolated; defer to keep this change focused on the soundness mechanism.
