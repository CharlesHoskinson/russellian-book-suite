# Tasks: booklogic-v0.6-predicate-uf-semantics

Detailed design in `design.md`. Each task is TDD-shaped: failing test citing the
REQ-ID → minimal impl → green → commit. One problem per PR. No AI attribution.
Run the suite via `cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest
tests -q`. Verify Rust via CI (`cargo check --features smt`), not locally.

## Phase A — OpenSpec record

- [ ] Task 0: OpenSpec record + branch `feat/booklogic-v0.6-predicate-uf` (this change)

## Phase B — Predicate-UF registry

- [ ] REQ-SMT-056 — Task 1: build `predicate_ufs` registry in `generate_axioms_source`
      from `_SCHEMA`; nil/empty `:arg-sorts` excluded. Unit test: a schema with one
      arg-sorted Bool predicate yields a one-entry registry; a nil-arity schema
      yields an empty registry.
- [ ] REQ-SMT-056 — Task 1b: add `_is_bool_sort` + `_sort_const` helpers (primitive
      `:int/:real/:bool/:string` → `Sort::int()/real()/bool()/string()`, custom →
      `Sort::uninterpreted`). Unit test each mapping.

## Phase C — FuncDecl preamble + plumbing

- [ ] REQ-SMT-057 — Task 2: thread `predicate_ufs` through `_emit_z3_block` →
      `_emit_bool_subexpr` / `_emit_quantifier_expr`. Emit one
      `FuncDecl::new(name, &[arg_sorts], &Sort::bool())` per needed predicate into the
      quantifier block scope; declared once per block. Test: emitted Rust contains
      exactly one `FuncDecl::new("contradicts"` for a body referencing it twice.

## Phase D — Application emission + validation

- [ ] REQ-SMT-058 — Task 3: keyword arm emits `<pred>_fn.apply(&[&a, &b]).as_bool().unwrap()`
      for registered predicates; args resolved via `bound_vars`/sort registry. Test:
      `(:contradicts ?a ?b)` in a forall body emits `contradicts_fn.apply(` and no
      `Bool::new_const`.
- [ ] REQ-SMT-059 — Task 4: arity + arg-sort validation against schema; mismatch →
      `CodegenError`. Test: 3-arg call to a 2-arg predicate raises; wrong-sort arg
      raises.
- [ ] REQ-SMT-058 — Task 4b: `_resolve_pred_arg` — `?var`→bound const (unbound →
      `CodegenError`), subject keyword → sort-typed const. Test both branches.

## Phase E — Backward-compat / determinism pin

- [ ] REQ-SMT-061 — Task 5: nil-arity predicates keep the opaque-`Bool::new_const`
      path. Determinism test: regenerate `axioms.rs` for bermuda + osmotic_pressure
      fixtures; assert byte-identical to a captured baseline (closes v0.5 REQ-SMT-055).

## Phase F — Soundness proof

- [ ] REQ-SMT-060 — Task 6: synthetic obligation-sort schema + entailed/non-entailed
      constraints. Fast layer: assert emitted Rust uses `apply(`. CI `--features smt`
      layer: entailed → `:unsat`, non-entailed → `:sat`.

## Phase G — Docs + golden fixture

- [ ] REQ-BOOKLOGIC-054 — Task 7: promote SUPPORT_MATRIX quantifier row to **wired**;
      replace the predicate-application caveat section with the UF semantics
      description; delete `TODO(Tier 3)` at `codegen_axioms.py:1297`. Drift lint passes.
- [ ] REQ-BOOKLOGIC-055 — Task 8: add boolean-connective, quantifier, and predicate-UF
      sections to `docs/booklogic-dsl-reference.md` under correct non-colliding numbers
      (fixes the v0.5 REQ-BOOKLOGIC-052 §2.6/§2.7 collision with defquery/defremedy).
- [ ] REQ-BOOKLOGIC-056 — Task 9: `tests/golden/predicate_uf_v0_6.edn` (entailed,
      non-entailed, arity-mismatch); golden test asserts per-case outcome.

## Phase H — End-to-end + PR

- [ ] REQ-SMT-061 — Task 10: `cargo check --features smt` green for osmotic_pressure
      and bermuda on CI (no local cargo).
- [ ] Task 11: Push + open PR (no REQ — controller-orchestrated).
