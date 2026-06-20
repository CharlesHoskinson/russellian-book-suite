# Repo design-intelligence KG implementation plan

> For agentic workers: execute this as a superpowers-style phased plan. Each
> phase ends with a review gate before moving on.

**Goal:** Build a source-backed design-intelligence graph that agents can use to
study and improve the repo's design and utility.

**Spec:** `openspec/changes/repo-design-intelligence-kg/`

**Primary surface:** `skills/book-knowledge` plus graphify output, OpenSpec,
docs, tests, and CI metadata.

## Phase 0: Contract

- [x] Create OpenSpec proposal/design/tasks.
- [x] Add spec deltas REQ-KG-047..056.
- [x] Add this superpowers plan.

Review gate:

- [ ] Confirm the requirements are crisp enough for TDD.
- [ ] Confirm the scope does not require committing generated graphify artifacts.

## Phase 1: Schema and fixture

- [x] Add design-intelligence entities to `kg-schema.edn`.
- [x] Create a small fixture repository tree under
  `skills/book-knowledge/tests/fixtures/design-kg/`.
- [x] Write schema tests first, then update the schema.

Review gate:

- [ ] A reviewer verifies no direct `pycozo` access is introduced.
- [ ] A reviewer verifies fixture rows cover all new entity families.

## Phase 2: Extractors

- [x] Implement OpenSpec requirement extraction.
- [x] Implement design-doc extraction.
- [x] Implement test and CI extraction.
- [x] Add deterministic golden rows for the fixture.

Review gate:

- [ ] A reviewer verifies the extractors are read-only.
- [ ] A reviewer verifies all rows carry source path and line.

## Phase 3: Traceability

- [x] Implement deterministic link promotion.
- [x] Store lexical/semantic candidates as evidence-only.
- [x] Add ambiguity tests proving weak candidates stay unpromoted.

Review gate:

- [ ] A reviewer attempts to refute promoted links in the fixture.
- [ ] A reviewer verifies canonical queries exclude unpromoted evidence.

## Phase 4: Query pack

- [x] Add named graph queries for impact, why, coverage gaps, stale docs,
  untested god nodes, claim grounding, and CI gates.
- [x] Add tests requiring provenance in every query row.

Review gate:

- [ ] A reviewer uses each query on the fixture and checks the evidence path.

## Phase 5: Whole-repo design audit

- [x] Regenerate the local graphify map.
- [x] Run the projection over the repo snapshot.
- [x] Produce `docs/audits/<date>-design-intelligence-kg/`.

Review gate:

- [ ] A reviewer maps findings back to graphify communities.
- [ ] A reviewer verifies each Important finding has file-line evidence and a
  concrete fix path.

## Phase 6: Operationalize

- [x] Add a runbook for rebuilding the graph and running the query pack.
- [x] Add CI-safe checks for extractor determinism.
- [x] Decide whether the audit artifact is advisory or merge-gating.

Review gate:

- [ ] A reviewer verifies the commands work from a clean checkout with graphify
  installed.
