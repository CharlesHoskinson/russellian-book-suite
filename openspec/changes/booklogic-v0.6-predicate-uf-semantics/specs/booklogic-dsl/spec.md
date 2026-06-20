# Capability delta: booklogic-dsl — change: booklogic-v0.6-predicate-uf-semantics

## ADDED Requirements

### Requirement: REQ-SMT-056 — Predicate-UF registry

`generate_axioms_source` SHALL build a predicate-uninterpreted-function registry
from the parsed `:predicates` schema map: every predicate whose `:arg-sorts` is
non-empty and whose `:return` resolves to the `Bool` sort SHALL be recorded with
its ordered argument sorts and a Bool return; predicates with `nil`/empty
`:arg-sorts` SHALL be excluded.

Rationale: the schema already carries `{:arg-sorts, :return}` (REQ-DSL-050..053);
the registry is the single source deciding, per predicate, between the sound
`apply` path and the legacy nullary path.

#### Scenario: arg-sorted Bool predicate is registered

- **WHEN** the schema declares `:contradicts {:arg-sorts [:obligation :obligation], :return :bool}`
- **THEN** `generate_axioms_source` records `contradicts` with two argument sorts and a Bool return
- **AND** `tests/test_codegen_axioms_predicate_uf.py::test_registry_includes_arg_sorted_bool_predicate` passes

#### Scenario: nil-arity predicate is excluded

- **WHEN** the schema declares `:herd-immunity-threshold {:arg-sorts nil, :return nil}`
- **THEN** the predicate is absent from the registry
- **AND** `::test_registry_excludes_nil_arity` passes

### Requirement: REQ-SMT-057 — FuncDecl preamble

For each registered predicate a constraint body references, the codegen SHALL emit
exactly one `FuncDecl::new(<name>, &[<arg-sort consts>], &Sort::bool())` within the
block scope, declared before first use and reused by every application in that block.

Rationale: a single shared `FuncDecl` makes two applications the same Z3 term —
the precondition for a quantifier to bind them. Block-local declaration matches the
existing `Sort::uninterpreted` sharing contract.

#### Scenario: one declaration per block regardless of use count

- **WHEN** a quantifier body references `(:contradicts ?a ?b)` twice
- **THEN** the emitted Rust contains exactly one `FuncDecl::new("contradicts"`
- **AND** `::test_funcdecl_declared_once_per_block` passes

### Requirement: REQ-SMT-058 — Apply emission

The codegen SHALL emit `<pred>_fn.apply(&[&arg…]).as_bool().unwrap()` for a
registered predicate application `(:pred arg…)` appearing in any Bool context
(assert head, boolean connective, or quantifier body), resolving each `?var`
argument through the in-scope `bound_vars` map and each sort-typed subject argument
to a constant of the declared argument sort.

Rationale: routing bound constants through `apply` replaces the opaque
`Bool::new_const` that ignored its arguments.

#### Scenario: predicate inside forall emits apply, not opaque Bool

- **WHEN** `(forall [(?a :obligation) (?b :obligation)] (=> (:contradicts ?a ?b) ...))` is compiled
- **THEN** the body emits `contradicts_fn.apply(&[&a_const, &b_const])`
- **AND** no `Bool::new_const("contradicts_a_b")` appears
- **AND** `::test_predicate_in_forall_emits_apply` and `::test_no_opaque_bool_for_registered_predicate` pass

#### Scenario: bound variable resolves to its quantifier constant

- **WHEN** `?a` appears as a predicate argument inside the binding `(?a :obligation)`
- **THEN** the emitted argument reference is the `a_const` declared for that binding
- **AND** `::test_bound_var_resolves_in_predicate_arg` passes

### Requirement: REQ-SMT-059 — Arity and sort validation

The codegen SHALL raise `CodegenError` naming the predicate and the mismatch, and
SHALL NOT emit Rust, when a registered predicate application's argument count or
argument sorts disagree with its schema declaration.

Rationale: arity/sort errors are author mistakes that must fail loud at compile
time, consistent with the undeclared-sort check (REQ-SMT-054).

#### Scenario: wrong arity raises

- **WHEN** `(:contradicts ?a ?b ?c)` is applied to a 2-argument predicate
- **THEN** a `CodegenError` naming `contradicts` and the arity mismatch is raised
- **AND** `::test_arity_mismatch_raises` passes

#### Scenario: wrong argument sort raises

- **WHEN** an argument whose value cannot match the declared argument sort is supplied
- **THEN** a `CodegenError` naming the sort mismatch is raised
- **AND** `::test_arg_sort_mismatch_raises` passes

### Requirement: REQ-SMT-060 — Quantifier soundness

The generated verifier SHALL report `:unsat` for a universally-quantified property
over a registered predicate together with a contradicting witness, and SHALL report
`:sat` for the same property without the witness.

Rationale: this is the soundness criterion the v0.5 structural encoder failed —
distinct opaque Bools made both cases `:sat`. Distinguishing them is the working
definition of "the quantifier actually constrains the predicate".

#### Scenario: entailed universal is unsat

- **GIVEN** a witness `(:contradicts :A :B)` and `(forall [(?a :obligation) (?b :obligation)] (=> (:contradicts ?a ?b) false))`
- **THEN** the `--features smt` verifier returns `:unsat`
- **AND** the unit layer asserts the emission uses `apply(`
- **AND** `::test_emits_apply_for_soundness` and CI `test_quantified_entailment_unsat` pass

#### Scenario: non-entailed universal is sat

- **GIVEN** the same property without the witness
- **THEN** the verifier returns `:sat`
- **AND** CI `test_quantified_non_entailment_sat` passes

### Requirement: REQ-SMT-061 — Determinism for shipped verifiers

For verifiers whose predicates are all nil-arity, the generated `axioms.rs` SHALL be
byte-identical before and after this change.

Rationale: the three shipped verifiers (bermuda, osmotic_pressure, epidemiology)
declare every predicate `{:arg-sorts nil}` and must observe zero behavioural change;
this also closes the deterministic-output pin v0.5 REQ-SMT-055 left open.

#### Scenario: nil-arity verifier output unchanged

- **WHEN** `axioms.rs` is regenerated for bermuda and osmotic_pressure
- **THEN** the output is byte-identical to the captured pre-change baseline
- **AND** `::test_shipped_verifier_axioms_byte_identical` passes

### Requirement: REQ-BOOKLOGIC-054 — SUPPORT_MATRIX promotion

`SUPPORT_MATRIX.md` SHALL list the `(forall / exists)` row as **wired** (no caveat),
SHALL describe the uninterpreted-function encoding in place of the deferred-to-Tier-3
caveat, and the `TODO(Tier 3)` comment at the predicate-application site SHALL be
removed. The SUPPORT_MATRIX drift lint SHALL pass.

Rationale: the documented soundness caveat is the user-visible contract; once the fix
lands it must read as sound, and the stale deferral must not linger.

#### Scenario: matrix and code reflect sound quantifiers

- **WHEN** the SUPPORT_MATRIX drift lint runs after this change
- **THEN** the quantifier row reads `wired` with no caveat
- **AND** no `TODO(Tier 3)` remains in `codegen_axioms.py`
- **AND** the drift lint and `::test_no_tier3_todo_remains` pass

### Requirement: REQ-BOOKLOGIC-055 — DSL reference operator docs

`docs/booklogic-dsl-reference.md` SHALL document boolean connectives, quantifiers,
and predicate-uninterpreted-function semantics under section numbers that do not
collide with the existing `defquery`/`defremedy` sections, each with an arity table
and a worked example.

Rationale: v0.5 REQ-BOOKLOGIC-052 was unsatisfiable as written (§2.6/§2.7 were taken);
the operator docs were never added. This change delivers them correctly.

#### Scenario: operator docs present under correct numbers

- **WHEN** the DSL-reference presence test runs
- **THEN** a boolean-connectives table, a quantifier table, and a predicate-UF worked example exist under non-colliding section numbers
- **AND** the presence test passes

### Requirement: REQ-BOOKLOGIC-056 — Golden fixture

`tests/golden/predicate_uf_v0_6.edn` SHALL contain at least three cases — an entailed
universal, a non-entailed universal, and an arity-mismatch — and a golden-comparison
test SHALL assert the expected `apply` emission or `CodegenError` per case.

Rationale: a committed golden fixture pins the emission shape against silent
regression, matching the v0.5 `extended_operators_v0_5.edn` pattern.

#### Scenario: golden cases match expected outcomes

- **WHEN** the golden test reads `predicate_uf_v0_6.edn`
- **THEN** each case's emission (or raised `CodegenError`) matches the recorded expectation
- **AND** `::test_golden_predicate_uf` passes
