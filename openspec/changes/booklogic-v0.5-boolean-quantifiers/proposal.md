# Change: booklogic-v0.5-boolean-quantifiers

**Sprint:** 5 (post-PR #80)
**Branch:** `feat/booklogic-v0.5-extended-operators`
**GitHub Milestone:** `booklogic-v0.5-boolean-quantifiers`

## Why

PR #80 (Tier 2F) shipped `<`, `<=`, `>`, `>=`, `/`, and `ite` at both the
assert-head and sub-expression levels. The remaining expressivity gap is boolean
head connectives (`and`, `or`, `not`, `=>`) and general quantifiers (`forall`,
`exists`). Without them, EpochPoET's consensus-protocol verifier cannot express:

- **Joint-threshold conjecture:** `(and (>= domain-count 3) (< joint-corruption 1/3) ...)`
- **Universal supersession:** `(forall [(?a obligation) (?b obligation)] (=> (:contradicts ?a ?b) (or (:supersedes ?a ?b) (:supersedes ?b ?a))))`
- **Existential provenance:** `(forall [(?o obligation)] (exists [(?r reference)] (:asserted-by ?o ?r)))`

Boolean heads and general quantifiers are the missing primitives. This change adds
them as a strict delta on top of PR #80 ancestry.

## What

Extend `codegen_axioms.py`'s `_emit_z3_block` dispatcher with four boolean arms
(`and`, `or`, `not`, `=>`) and two quantifier arms (`forall`, `exists`). Introduce
`_emit_bool_subexpr` as the composable helper for Bool-valued sub-expressions. Add
`bound_vars` threading so bound variable references (`?x`) inside quantifier bodies
resolve to their Z3 constants. Validate sort keywords against the declared-sort set
built in `generate_axioms_source`; undeclared sorts raise `CodegenError`. Update
SUPPORT_MATRIX and DSL reference docs.

## Requirements

| REQ id | One-line acceptance criterion |
|---|---|
| REQ-SMT-046 (`and`) | `(and <bool> <bool>+)` at assert head emits `Bool::and(ctx, &[...])` and passes cargo check |
| REQ-SMT-047 (`or`) | `(or <bool> <bool>+)` at assert head emits `Bool::or(ctx, &[...])` and passes cargo check |
| REQ-SMT-048 (`not`) | `(not <bool>)` at assert head emits `<inner>.not()` and passes cargo check |
| REQ-SMT-049 (`=>`) | `(=> <bool> <bool>)` at assert head emits `<premise>.implies(&<conclusion>)` and passes cargo check |
| REQ-SMT-050 (Bool-subexpression helper) | `_emit_bool_subexpr` composes all comparison, equality, approx-equality, and boolean heads recursively; used by `and`/`or`/`not`/`=>`/`forall`/`exists` arms |
| REQ-SMT-051 (`forall`) | `(forall [(?var :sort) ...] <body>)` emits `ctx.mk_forall_const(...)` with correct bound constants and passes cargo check |
| REQ-SMT-052 (`exists`) | `(exists [(?var :sort) ...] <body>)` emits `ctx.mk_exists_const(...)` with correct bound constants and passes cargo check |
| REQ-SMT-053 (bound-variable refs) | `?var` symbols inside a quantifier body resolve to the bound Z3 constant; a bare `?var` outside any quantifier scope raises `CodegenError: unbound variable` |
| REQ-SMT-054 (sort-registry check) | A sort keyword used in a quantifier binding that is not listed in the project's `sorts.edn` raises `CodegenError: sort '...' not declared` |
| REQ-SMT-055 (cargo check + deterministic output) | Existing bermuda and osmotic_pressure verifiers compile without error and produce byte-identical axioms.rs output post-merge |
| REQ-BOOKLOGIC-051 (SUPPORT_MATRIX) | SUPPORT_MATRIX.md gains two new rows: one for boolean connectives, one for quantifiers; drift lint test passes |
| REQ-BOOKLOGIC-052 (DSL ref §2.6, §2.7) | `docs/booklogic-dsl-reference.md` gains §2.6 (boolean connectives) and §2.7 (quantifiers), each with arity table and worked example |
| REQ-BOOKLOGIC-053 (golden fixture) | `tests/golden/extended_operators_v0_5.edn` contains 6 cases; a golden-comparison test asserts the expected Z3 call string appears in codegen output for each case |

## Out of scope

- **Bounded `(forall ?x in vec ...)`** — Tier 2 Phase G, a separate plan. Operates
  over a known-size vector, not the sort registry. Orthogonal to this change.
- **Trigger pattern annotations (`:trigger`)** — deferred to Tier 5. v0.5 emits
  empty trigger patterns; Z3 falls back to MBQI.
- **New `D14` defect class** — not needed. `CodegenError` raised at compile time is
  loud and visible; no new runtime defect class warranted.
- **Ratio EDN literal parsing (`1/3`, `1/4`)** — EpochPoET's constraints.edn rewrites
  ratio literals to `(/ 1 3)` / `(/ 1 4)` in a follow-up commit. EDN-reader changes
  are a separate future enhancement.

## Acceptance

- Tests `test_generate_and_assertion`, `test_generate_or_assertion`,
  `test_generate_nested_and_or`, `test_generate_not_assertion`,
  `test_generate_implies_assertion` all pass
- Tests in `test_codegen_axioms_quantifiers.py` all pass (4 tests)
- Bound-variable resolution tests pass (2 tests)
- Golden fixture comparison test passes
- `cargo check --features smt` succeeds for osmotic_pressure and bermuda
- Deterministic-output pin: byte-identical axioms.rs before and after merge
- SUPPORT_MATRIX drift lint passes
- All 13 REQ IDs are test-covered

## Implementation notes

See `docs/plans/2026-05-18-booklogic-v0.5-extended-operators.md` — 7 phases,
Phases A–F.
