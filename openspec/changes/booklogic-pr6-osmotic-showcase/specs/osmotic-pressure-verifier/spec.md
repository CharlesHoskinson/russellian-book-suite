# Capability delta: osmotic-pressure-verifier — change: booklogic-pr6-osmotic-showcase

## ADD

### REQ-OSMOTIC-001 — Ubiquitous

The `verifiers/osmotic_pressure/` directory shall exist and contain a
project scaffolded by `python -m scripts.scaffold_project --name "Osmotic
pressure" --slug osmotic_pressure`.

**Rationale:** First non-Bermuda verifier.
**Tested by:** `verifiers/osmotic_pressure/tests/test_project_layout.py::test_scaffolded` (added in pr6 T1.1)

### REQ-OSMOTIC-010 — Ubiquitous

`verifiers/osmotic_pressure/rules/sorts.edn` shall declare `:solution`
in addition to the primitives.

**Rationale:** The chemistry domain needs a solution sort.
**Tested by:** `tests/test_booklogic_source_shape.py::test_solution_sort` (added in pr6 T2.1)

### REQ-OSMOTIC-011 — Ubiquitous

`verifiers/osmotic_pressure/rules/predicates.edn` shall declare
`:osmotic-pressure-pa`, `:vant-hoff-i`, `:molarity`, `:temperature-k`,
each typed as `[:solution] :real`.

**Rationale:** Van 't Hoff equation needs these four observables.
**Tested by:** `test_booklogic_source_shape.py::test_four_predicates` (added in pr6 T2.2)

### REQ-OSMOTIC-012 — Ubiquitous

`verifiers/osmotic_pressure/rules/lifts.edn` shall declare at least one
`deflift` for prose extraction in the osmotic-pressure domain.

**Rationale:** Demonstrates lift usage in a non-book domain.
**Tested by:** `test_booklogic_source_shape.py::test_at_least_one_lift` (added in pr6 T2.3)

### REQ-OSMOTIC-013 — Ubiquitous

`verifiers/osmotic_pressure/rules/constraints.edn` shall declare one
`defconstraint` encoding `π ≈ i·M·R·T` (with `R = 8.314`) using `~=`
with `:tolerance 0.03` for relative 3% tolerance.

**Rationale:** Headline showcase constraint; exercises the `~=` operator.
**Tested by:** `test_booklogic_source_shape.py::test_vant_hoff_constraint_with_relative_tolerance` (added in pr6 T2.4)

### REQ-OSMOTIC-020 — Ubiquitous

`verifiers/osmotic_pressure/fixtures/claims_clean.jsonl` shall contain
four verified claims declaring i=2, M=0.154 mol/L, T=298.15 K,
π=780202.5 Pa for a single solution entity.

**Rationale:** Test fixture matching the spec example.
**Tested by:** `verifiers/osmotic_pressure/tests/test_smoke.py::test_clean_sat` (added in pr6 T3.1, T5.1)

### REQ-OSMOTIC-021 — Ubiquitous

`verifiers/osmotic_pressure/fixtures/claims_doctored.jsonl` shall contain
four verified claims identical to the clean fixture except `i=1`.

**Rationale:** Doctored case must trigger unsat.
**Tested by:** `test_smoke.py::test_doctored_unsat` (added in pr6 T3.2, T5.2)

### REQ-OSMOTIC-030 — Event-driven

When the BookLogic compiler is invoked against
`verifiers/osmotic_pressure/`, it shall produce
`verifiers/osmotic_pressure/rust-verifier/src/axioms.rs` containing the
desugared Van 't Hoff `~=` assertion.

**Rationale:** Codegen smoke for the showcase domain.
**Tested by:** `tests/test_codegen.py::test_vant_hoff_axiom_emitted` (added in pr6 T4.1)

### REQ-OSMOTIC-031 — Event-driven

When `cargo build --manifest-path verifiers/osmotic_pressure/rust-verifier/Cargo.toml
--features z3,bundled` runs on `ubuntu-latest`, it shall complete with exit 0.

**Rationale:** Cargo build is the canonical CI gate.
**Tested by:** CI job `osmotic-pressure-smoke` (added in pr6 T4.2, T6.1)

### REQ-OSMOTIC-040 — Event-driven

When the osmotic-pressure verifier is invoked against `claims_clean.jsonl`,
the verdict shall be `:sat`.

**Rationale:** Clean-case assertion.
**Tested by:** `test_smoke.py::test_clean_sat` (added in pr6 T5.1)

### REQ-OSMOTIC-041 — Event-driven

When the osmotic-pressure verifier is invoked against `claims_doctored.jsonl`,
the verdict shall be `:unsat`, and the unsat core shall contain the
i=1 claim id.

**Rationale:** Doctored-case assertion; demonstrates traceability.
**Tested by:** `test_smoke.py::test_doctored_unsat` (added in pr6 T5.2)

### REQ-OSMOTIC-050 — Ubiquitous

The `.github/workflows/ci.yml` workflow shall include a job
`osmotic-pressure-smoke` on `ubuntu-latest` that on every PR scaffolds
the project (or uses the committed copy), runs `cargo build`, and exercises
both fixture ledgers, asserting `:sat` and `:unsat` respectively.

**Rationale:** CI gates the showcase claim end-to-end.
**Tested by:** Workflow run (added in pr6 T6.1)

## MODIFY

(none)

## REMOVE

(none)
