# Change: booklogic-v0.6-predicate-uf-semantics

**Sprint:** 2 (post-#229 / Sprint 1 verifier-chain)
**Branch:** `feat/booklogic-v0.6-predicate-uf`
**GitHub Milestone:** `booklogic-v0.6-predicate-uf-semantics`
**Capability:** `booklogic-dsl`

## Why

v0.5 (`booklogic-v0.5-boolean-quantifiers`) shipped `forall`/`exists` with
correct **structural** wiring: `_emit_quantifier_expr` emits `ast::forall_const`
/ `ast::exists_const` over typed bound constants. But a Keyword-headed predicate
inside a quantifier body — `(:contradicts ?a ?b)` — still lowers to an *opaque*
`Bool::new_const("contradicts_a_b")` (`codegen_axioms.py:1300`). Z3 sees one
fresh Bool per textual occurrence, so the bound variables never enter the
predicate. A universally-quantified property over that predicate is therefore
**not enforced across instantiations**: the solver cannot distinguish an entailed
universal from a non-entailed one. The repo documents this as a soundness caveat
(`SUPPORT_MATRIX.md` §"Quantifier predicate-application semantics") and defers the
fix with `TODO(Tier 3)` at `codegen_axioms.py:1297`.

Until this lands, a verifier verdict over a quantified predicate is a *structural*
check ("did the framework wire the quantifier?") rather than a *soundness* proof
("did Z3 verify the universal property?"). EpochPoET's consensus-protocol
conjectures (universal supersession, existential provenance) need the latter.

This change closes the gap: predicates whose schema return-sort is `Bool` become
Z3 **uninterpreted functions** (`FuncDecl`), and predicate applications emit
`<pred>_fn.apply(&[&a, &b])`. The bound constants now flow into the function, so
the quantifier constrains the predicate across its domain — quantified properties
become sound.

## What

1. Build a **predicate-UF registry** in `generate_axioms_source` from the parsed
   `schema[:predicates]` map (already carries `{:arg-sorts, :return}`,
   REQ-DSL-050..053). Every predicate with a non-empty `:arg-sorts` and a `Bool`
   `:return` becomes a `FuncDecl` declaration.
2. Emit the `FuncDecl` declarations **once** into a shared preamble helper, so all
   asserts in a check share the same function symbols under the thread-local
   context (mirrors how `Sort::uninterpreted` is shared in
   `_emit_quantifier_expr`).
3. In `_emit_bool_subexpr`'s Keyword-headed arm, replace the opaque
   `Bool::new_const(...)` with `<pred>_fn.apply(&[&arg, ...]).as_bool().unwrap()`
   **when the predicate is in the registry**. Arguments resolve through
   `bound_vars` (quantifier-bound `?v` → its `Dynamic` const) and the sort
   registry (subject keywords → sort-typed consts).
4. Validate predicate **arity and argument sorts** against the schema; a mismatch
   raises `CodegenError` at compile time (loud, like the existing sort check).
5. Preserve the **opaque-Bool path** for zero-arity predicates (`:arg-sorts nil`),
   so the three shipped verifiers (bermuda, osmotic_pressure, epidemiology) whose
   predicates are all nil-arity produce **byte-identical** `axioms.rs` — the
   determinism pin v0.5 REQ-SMT-055 never formally closed.
6. Promote the `SUPPORT_MATRIX` quantifier row from **wired-with-caveat** →
   **wired**; delete the `TODO(Tier 3)` and the deferral note.
7. Fix the v0.5 doc-numbering defect: REQ-BOOKLOGIC-052 asked for DSL-reference
   §2.6 (boolean connectives) + §2.7 (quantifiers), but those section numbers were
   already `defquery`/`defremedy`. Add the operator docs under correct, non-colliding
   section numbers, plus a §for predicate-UF semantics.

## Requirements

| REQ id | One-line acceptance criterion |
|---|---|
| REQ-SMT-056 (UF registry) | `generate_axioms_source` builds a predicate→FuncDecl registry from `schema[:predicates]` for every entry with non-empty `:arg-sorts` and a Bool `:return` |
| REQ-SMT-057 (FuncDecl preamble) | The registry emits one `FuncDecl::new(name, &[arg_sorts], &Sort::bool())` per Bool predicate into a shared preamble helper; declared once, reused by every assert |
| REQ-SMT-058 (apply emission) | A registered predicate `(:pred a b)` in any Bool context emits `<pred>_fn.apply(&[&a, &b]).as_bool().unwrap()`, with args resolved via `bound_vars`/sort registry, and passes cargo check |
| REQ-SMT-059 (arity/sort check) | A predicate application whose arg count or arg sorts disagree with the schema raises `CodegenError: predicate '...' arity/sort mismatch` |
| REQ-SMT-060 (soundness) | An entailed universal (`(forall [(?a :s)(?b :s)] (=> (:p ?a ?b) (:q ?a ?b)))` with a contradicting witness) yields `:unsat`; a non-entailed one yields `:sat` — the structural-only encoder could not distinguish these |
| REQ-SMT-061 (determinism) | The shipped verifiers (all nil-arity predicates) keep the opaque-Bool path and produce byte-identical `axioms.rs` before/after this change (closes v0.5 REQ-SMT-055) |
| REQ-BOOKLOGIC-054 (SUPPORT_MATRIX) | The quantifier row reads **wired** (no caveat); the predicate-application caveat section is replaced with the UF semantics description; drift lint passes |
| REQ-BOOKLOGIC-055 (DSL ref) | `docs/booklogic-dsl-reference.md` documents boolean connectives, quantifiers, and predicate-UF semantics under correct non-colliding section numbers, each with an arity table and a worked example |
| REQ-BOOKLOGIC-056 (golden fixture) | `tests/golden/predicate_uf_v0_6.edn` contains ≥3 cases (entailed, non-entailed, arity-mismatch); a golden test asserts the expected `apply`/`CodegenError` outcome per case |

## Out of scope

- **Non-Bool uninterpreted functions** (predicates returning `:int`/`:real`,
  e.g. `(:weight ?x)` used as a term). This change handles Bool-returning
  predicates only; term-valued UFs are a follow-up if a verifier needs them.
- **Trigger/pattern annotations (`:trigger`)** — still deferred; quantifiers emit
  empty patterns and Z3 falls back to MBQI (unchanged from v0.5).
- **Schema authoring ergonomics** (inferring `:arg-sorts` from usage). Authors
  declare arg-sorts explicitly in `predicates.edn`; inference is a separate change.
- **Bounded `(forall ?x in vec ...)`** — Tier 2 Phase G, vector-domain, orthogonal.

## Acceptance

- `tests/test_codegen_axioms_predicate_uf.py` all pass (registry, apply emission,
  arity/sort error, determinism pin)
- `tests/test_codegen_axioms_quantifiers.py` still pass (no structural regression)
- Soundness test (REQ-SMT-060) passes: entailed → `:unsat`, non-entailed → `:sat`
- `cargo check --features smt` succeeds for osmotic_pressure and bermuda
- Byte-identical `axioms.rs` for the shipped verifiers (REQ-SMT-061)
- Golden fixture comparison test passes
- SUPPORT_MATRIX drift lint passes; the `TODO(Tier 3)` is gone
- All 9 REQ IDs are test-covered

## Implementation notes

See `design.md` for the FuncDecl emission shape, argument resolution, and the
preamble-sharing strategy. TDD plan steps live in `tasks.md`.
