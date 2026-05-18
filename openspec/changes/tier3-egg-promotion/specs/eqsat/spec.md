# Capability delta: eqsat — change: tier3-egg-promotion

This change introduces a new capability `eqsat`, the framework's
equality-saturation surface. Today `defrule` and
`defconstraint :backend :egg` are stub / DROP per
`SUPPORT_MATRIX.md`. After this change both flip to "wired".

## ADD

### REQ-EQSAT-040 — Ubiquitous

The framework SHALL ship a working egg-rs integration in
`verifiers/*/rust-verifier/src/eqsat.rs` that builds an
`egg::EGraph<BookLogicLang, ()>` from the BookLogic `defrule`
set. The integration SHALL expose at least:

- `build_egraph(terms, rules) -> EGraph` to seed an e-graph,
- `canonicalise(expr, rules) -> Expr` to run saturation and
  extract a cost-minimal representative via
  `egg::Extractor::new(&egraph, AstSize)`.

The eqsat module SHALL compile under the `eqsat` Cargo feature
and import `egg = "0.10"` (already declared optional in each
verifier's `Cargo.toml`).

**Rationale:** Replaces the one-line stub with a real
integration; gives `defrule` semantic teeth.
**Tested by:** `verifiers/osmotic_pressure/rust-verifier/tests/eqsat_smoke.rs::saturation_completes_for_one_rule` (added in G1.3)

### REQ-EQSAT-041 — Ubiquitous

During codegen, the framework SHALL run equality saturation on
each `defconstraint` LHS/RHS pair via `eqsat::canonicalise(...)`
and store the post-saturation canonical form in the generated
`axioms.rs`. The canonical form SHALL be the cost-minimal
extracted member of the LHS's e-class under `AstSize`.

**Rationale:** Two algebraically equivalent author-written
constraints must compile to the same Z3 assertion; the e-graph
is the canonical-form oracle.
**Tested by:** `skills/neurosym-forge/tests/test_codegen_axioms.py::test_equivalent_forms_yield_identical_axioms` (added in G2.3)

### REQ-EQSAT-042 — Ubiquitous

The Z3 axiom emitter (`_emit_z3_block` in
`codegen_axioms.py`) SHALL emit canonical forms (post-saturation,
extracted from the e-graph) rather than the BookLogic surface
forms. The pre-saturation form SHALL be recorded in a
companion comment on the emitted line for debuggability.

**Rationale:** Closes the path where two constraints that differ
only in term-order produce non-identical Z3 input strings.
**Tested by:** `tests/test_codegen_axioms.py::test_emitted_axiom_carries_pre_canonical_comment` (added in G2.3)

### REQ-EQSAT-043 — Optional feature

WHERE a `defconstraint` form declares `:backend :egg`, the
framework SHALL prove the constraint via `eqsat::prove_equiv(lhs,
rhs) -> ProofResult` (a thin wrapper over egg's `equivs` API)
instead of Z3. The verdict SHALL include an `:egg-proofs` field
mapping each `:egg`-backed constraint ID to one of
`:proved`, `:not-proved`, or `:disproved`.

**Rationale:** The DSL has advertised `:backend :egg` as a
supported route since v0.4; this REQ retires the silent DROP
in `codegen_axioms.py:139`.
**Tested by:** `tests/eqsat_backend.rs::egg_backed_constraint_appears_in_verdict` (added in G3.3)

### REQ-EQSAT-044 — Unwanted behaviour

IF a `defrule` introduces an infinite rewrite loop (e.g.
`:lhs ?x :rhs (* ?x 1)`), THEN equality saturation SHALL bail
at a configurable budget (node count, iteration count, or
wall-clock time) and surface a structured warning entry of the
shape `{:phase :eqsat :reason :budget-exceeded :rule "R###-..."}` 
on the verdict's `:warnings` list. The constraint SHALL still
be asserted using the best canonical form available before the
budget fired; it SHALL NOT be silently dropped. Budget defaults:
node-count 10000 (`VERIFIER_EQSAT_NODE_LIMIT`), iter-count 30
(`VERIFIER_EQSAT_ITER_LIMIT`), wall-clock 5000 ms
(`VERIFIER_EQSAT_TIMEOUT_MS`).

**Rationale:** Diverging rewrite sets must produce a loud,
actionable failure surface; no Z3 input should disappear into
the budget gap.
**Tested by:** `tests/eqsat_budget.rs::diverging_rule_emits_budget_warning_and_falls_back` (added in G4.3)

### REQ-EQSAT-045 — Ubiquitous

`skills/neurosym-forge/SUPPORT_MATRIX.md` SHALL be updated as
part of this change so that:

- the `defrule` row's Status flips from `stub` to `wired`,
- the `defconstraint :backend :egg` row's Status flips from
  `DROP` to `wired`,
- the "Roadmap pointers" Tier 3 line is removed,
- the "stub" and "DROP" legend entries no longer reference
  `defrule` or `:egg`.

The drift-lint `tests/test_support_matrix.py` SHALL pass against
the updated matrix after `codegen_axioms.py` and `eqsat.rs`
land.

**Rationale:** The matrix is the framework's promise surface;
landing the wiring without updating the matrix would leave
authors believing the path is still a stub.
**Tested by:** `tests/test_support_matrix.py::test_matrix_matches_codegen_after_tier3` (added in G5.1)

### REQ-EQSAT-046 — Ubiquitous

A new test file
`verifiers/osmotic_pressure/rust-verifier/tests/eqsat_canonical.rs`
SHALL exercise a 3-rule rewrite set (commutativity, associativity,
and identity for `*`) against a fixture of at least three
input expressions, asserting that all inputs extract to the
same canonical form. A sibling
`verifiers/bermuda/rust-verifier/tests/eqsat_canonical.rs`
SHALL exist mirroring the osmotic-pressure fixture, so the
bermuda verifier's integration is exercised on the same
guarantees.

**Rationale:** Integration coverage is mandatory for a backend
moving from stub to wired; the canonical-form invariant is the
single observable that proves saturation is actually running.
**Tested by:** `verifiers/osmotic_pressure/rust-verifier/tests/eqsat_canonical.rs::three_rule_fixture_collapses_to_one_form` and the bermuda mirror (added in G6.2)
