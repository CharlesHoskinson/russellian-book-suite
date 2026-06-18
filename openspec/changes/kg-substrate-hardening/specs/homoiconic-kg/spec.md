# Capability: homoiconic-kg (delta for kg-substrate-hardening)

This change EXTENDS the `homoiconic-kg` capability. It ADDS requirements
REQ-KG-032 through REQ-KG-037. It hardens REQ-KG-002 (single Cozo store),
REQ-KG-002b (seam isolation), REQ-KG-007 (swappable backend), and REQ-KG-008
(determinism) without altering them.

EARS classification is noted per requirement. Each requirement leads with its
subject and SHALL/SHALL NOT; the EARS trigger/condition is in the requirement
text and pinned by its scenarios.

## Definitions

- **conformance harness** — the dual-run test rig behind `cozo_store` that runs
  a frozen EDN query fixture against both backends and asserts equality.
- **dual-run** — executing the same fixture against Cozo and the reference backend
  and comparing their result sets.
- **reference backend** — a small EDN/Datalog evaluator (DataScript-class or a
  pure-Python EDN Datalog evaluator) covering a declared rule subset; authoring-time
  and test only, never the production store.
- **canonical ordering** — the fixed total order over result rows (column order then
  lexicographic row order) under which two result sets are compared.
- **switch-trigger** — a documented condition under which a backend swap is
  reconsidered (not performed automatically).

## ADDED Requirements

### Requirement: REQ-KG-032 — Conformance harness over frozen fixtures (Ubiquitous)

The framework SHALL provide a conformance harness behind the `cozo_store` seam that
runs a set of frozen EDN query fixtures, reaching the store only through the seam
(REQ-KG-002b).

Rationale: a frozen fixture set is the artifact that makes a future backend swap
cheap to evaluate; routing it through the seam keeps the `pycozo` engine isolated.

#### Scenario: harness runs the frozen fixtures through the seam

- **WHEN** the conformance harness runs on the declared fixture set
- **THEN** each frozen EDN fixture executes against the store via `cozo_store`, with no module bypassing the seam
- **AND** `tests/test_substrate_conformance.py::test_harness_runs_frozen_fixtures` passes

### Requirement: REQ-KG-033 — Dual-run result-set equality (Event-driven)

When a fixture runs against both Cozo and the reference backend, the system SHALL
find their outputs result-set equal under canonical ordering.

Rationale: dual-run equality is the working definition of "the reference backend
reproduces the rule surface"; it is what turns the seam from a shape into a proof.

#### Scenario: both backends agree on a fixture

- **WHEN** a declared-subset fixture runs against Cozo and against the reference backend
- **THEN** the two result sets are result-set equal under canonical ordering
- **AND** `tests/test_substrate_conformance.py::test_dual_run_result_set_equal` passes

### Requirement: REQ-KG-034 — Reference backend is authoring-time only (Ubiquitous)

The framework SHALL provide a reference backend that evaluates a declared rule subset
and SHALL NOT use it as the production store; the production store remains the single
Cozo store of REQ-KG-002, which stays invariant.

Rationale: the reference backend buys swap optionality and dual-run evidence; making
it the production path would break the single-store contract and the offline embedded
constraints Cozo satisfies.

#### Scenario: reference backend covers the subset and is never the production store

- **WHEN** the reference backend is loaded for the declared rule subset
- **THEN** it evaluates that subset, and the production query path still resolves through the single Cozo store
- **AND** `tests/test_substrate_conformance.py::test_reference_backend_is_authoring_only` passes

### Requirement: REQ-KG-035 — Canonical result ordering (Ubiquitous)

Query result sets SHALL be canonically ordered before comparison so that dual-run
comparison is deterministic.

Rationale: Cozo and the reference backend do not guarantee row order; a pinned
canonical order is what makes REQ-KG-033's equality decidable and reconciles with
REQ-KG-008's determinism clause.

#### Scenario: ordering is fixed and deterministic

- **WHEN** a fixture's result set is canonically ordered twice
- **THEN** the two orderings are byte-identical, and the order is independent of backend row emission
- **AND** `tests/test_substrate_conformance.py::test_canonical_ordering_deterministic` passes

### Requirement: REQ-KG-036 — Documented switch-trigger list (Ubiquitous)

The framework SHALL carry a documented switch-trigger list stating the explicit
conditions under which a backend swap is reconsidered: Python or platform support
breaks; an unpatchable correctness or security issue arises; the reference backend
reproduces the rule surface acceptably; or the embedded / Python-primary / offline
constraints are relaxed.

Rationale: an explicit trigger list keeps the "do not migrate now" verdict
reviewable; a swap is a recorded decision against named conditions, not a reflex.

#### Scenario: the switch-trigger list is present and names the triggers

- **WHEN** the substrate documentation is checked
- **THEN** the switch-trigger list exists and names the four triggers
- **AND** `tests/test_substrate_conformance.py::test_switch_trigger_doc_lists_triggers` passes

### Requirement: REQ-KG-037 — Divergence fails loudly (Unwanted)

If the reference backend and Cozo diverge on a fixture, then the harness SHALL fail
loudly and SHALL name the fixture and the diverging rows.

Rationale: a silent or unlabelled divergence is worthless as swap evidence; the
failure must point at the fixture and the exact rows so the gap is actionable.

#### Scenario: a divergence names the fixture and the rows

- **WHEN** the reference backend and Cozo produce different result sets for a fixture
- **THEN** the harness fails, naming the diverging fixture and the rows present in one backend but not the other
- **AND** `tests/test_substrate_conformance.py::test_divergence_fails_and_names_rows` passes
