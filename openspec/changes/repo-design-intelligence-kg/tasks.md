# Tasks

## Phase 0: Contract

- [x] Write the OpenSpec proposal, design, and task plan.
- [x] Add homoiconic-kg spec deltas for the design-intelligence graph.

## Phase 1: Schema and fixtures

- [x] Add `design-requirement`, `design-decision`, `test-case`,
  `ci-workflow`, `ci-job`, `operator-command`, and `traceability-link` to
  `kg-schema.edn`. Satisfies REQ-KG-047.
- [x] Add a small fixture tree under `skills/book-knowledge/tests/fixtures/design-kg/`
  with one requirement, one design decision, one test, one workflow, and one
  graphify code node. Satisfies REQ-KG-047, REQ-KG-048, REQ-KG-050.
- [x] Add schema tests proving the new entities, identity columns, and relation
  targets exist. Satisfies REQ-KG-047.

## Phase 2: Deterministic extractors

- [x] Implement the OpenSpec extractor for EARS requirements and scenarios.
  Satisfies REQ-KG-048, REQ-KG-053.
- [x] Implement the design-doc extractor for decisions, risks, non-goals,
  alternatives, and operator commands. Satisfies REQ-KG-048, REQ-KG-053.
- [x] Implement the test and CI extractor for pytest/Rust/cljs tests,
  workflows, jobs, matrix selectors, and required checks. Satisfies REQ-KG-050,
  REQ-KG-053.
- [x] Add determinism tests over the fixture tree with canonical row ordering.
  Satisfies REQ-KG-053.

## Phase 3: Traceability links

- [x] Implement deterministic requirement-to-code, requirement-to-test,
  requirement-to-CI, decision-to-code, and test-to-code linking. Satisfies
  REQ-KG-049, REQ-KG-051.
- [x] Store weak lexical or semantic matches as unpromoted evidence-only links.
  Satisfies REQ-KG-049, REQ-KG-055.
- [x] Add tests proving ambiguous links are not promoted automatically. Satisfies
  REQ-KG-055.

## Phase 4: Query pack

- [x] Add named queries for `impact`, `why`, `coverage-gaps`, `stale-docs`,
  `untested-god-nodes`, `claim-grounding`, and `ci-gates`. Satisfies
  REQ-KG-051, REQ-KG-052.
- [x] Add tests requiring every query row to include source path and line
  provenance. Satisfies REQ-KG-052.

## Phase 5: Audit artifact

- [x] Generate a local design-intelligence graph from the repo snapshot.
  Satisfies REQ-KG-056.
- [x] Produce a graphify-community coverage report under `docs/audits/`.
  Satisfies REQ-KG-054, REQ-KG-056.
- [x] Add a runbook for regenerating the design-intelligence graph and reading
  the query outputs. Satisfies REQ-KG-052, REQ-KG-056.

## Phase 6: Review gates

- [x] Run a spec-compliance review against REQ-KG-047..056.
- [x] Run a code-quality review focused on extractor determinism,
  source-provenance quality, and no backend bypass.
- [x] Run the book-knowledge targeted test suite and the repo doc checks.
