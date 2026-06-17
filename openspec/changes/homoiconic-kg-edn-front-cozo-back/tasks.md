# Tasks: homoiconic-kg-edn-front-cozo-back

Umbrella change. Work is sequenced P0–P5; **P0 + P1 are the first implementation
plan** (`docs/superpowers/plans/2026-06-16-homoiconic-kg-p0p1.md`). P2–P5 are
follow-on specs. Every task is TDD-shaped: failing test citing the REQ-ID →
minimal impl → green → commit. Verify Rust/cljs via CI.

## Phase A — OpenSpec record
- [ ] Task 0: OpenSpec record + branch `feat/homoiconic-kg` (this change)
- [ ] Task 0b: auditor-agent review of every EARS requirement; fixes folded in

## P0 — Homoiconic store stood up (first plan)
- [ ] REQ-KG-005 — Task P0.1: characterization harness — capture golden fixtures
      for the 8 SPARQL queries, the SHACL report, and D9–D11 on the bermuda
      workspace; commit under `tests/golden/kg/`.
- [ ] REQ-KG-001 — Task P0.2: author `kg-schema.edn` (entities/attributes/
      relations); schema-presence test.
- [ ] REQ-KG-002 — Task P0.3: `cozo_store.py` over `pycozo`; create relations from
      `kg-schema.edn`; round-trip load/query; validate `pip install
      "pycozo[embedded]"` on all 3 CI runners.
- [ ] REQ-KG-007 — Task P0.4: backend-agnostic seam interface + contract test
      against an in-memory stub backend.
- [ ] REQ-KG-003 — Task P0.5: booklogic→CozoScript compiler skeleton (pure fn) +
      EDN→CozoScript golden unit tests; undeclared-entity error.
- [ ] REQ-KG-004 — Task P0.6: `ledger→cozo` projector (parallel to RDF; ledger
      unchanged) + projection test.
- [ ] REQ-KG-008 — Task P0.7: determinism pin (two-run byte-identical) for
      projector + one query.

## P1 — Competency queries ported (first plan)
- [ ] REQ-KG-006 — Task P1.1: port `unsupported_claims` to booklogic EDN→Cozo;
      golden-match.
- [ ] REQ-KG-006 — Task P1.2: port the 3 remaining coverage queries
      (`chapter_evidence_coverage`, `orphan_wiki_pages`, `stale_after_source_refresh`).
- [ ] REQ-KG-006 — Task P1.3: port `contradiction_scan` (consistency).
- [ ] REQ-KG-006 — Task P1.4: port the 3 defeasible queries
      (`contested-rebuttal-window`, `posterior-floor`, `rebuttal-presence`).
- [ ] REQ-KG-006 — Task P1.5: switch `run_competency_queries` to the EDN→Cozo path
      behind a flag; both paths green against the golden harness.

## P4 — graphify fusion (LANDED on main, PR #252)
- [x] `graph.json` → Cozo `code-node`/`code-edge` loader (P4.1) + validation
- [x] Cross-graph code↔claim capability/acceptance test + `code-claim-link` (P4.3)
- [ ] Recompute god-nodes/communities in-engine (PageRank/Louvain) — match graphify (P4.2, deferred)
- [ ] Optional CLI surface (P4.4, deferred)

## The cutover (second plan — `docs/superpowers/plans/2026-06-17-homoiconic-kg-cutover.md`)

Sequenced as PR-sized phases; each is characterization-guarded and independently
shippable. The legacy stack stays in parallel until the final gate is green.

### C0 — Characterization completion (REQ-KG-014)
- [ ] Freeze SHACL conformance/violation goldens (bermuda + violating fixture)
- [ ] Freeze D9–D11 consistency goldens (bermuda + violating fixture); non-vacuity test

### P2 — SHACL → EDN constraints
- [ ] REQ-KG-009 / REQ-KG-020 — status vocabulary single EDN source feeding the
      schema enum, the (replacement) constraint, AND `claim_validator.VALID_TRANSITIONS`
- [ ] REQ-KG-003/012 — booklogic `defconstraint` → Cozo violation-rule compiler;
      port the 4 property constraints + 2 `sh:sparql` constraints; golden-match
- [ ] REQ-KG-013 — `validate_shacl(layout)->ShaclReport` reimplemented over the Cozo
      path (contract preserved), routed through `cozo_store`; book-compose callers unchanged
- [ ] Recursive-SHACL shapes: choose + document a fixpoint semantics (none currently
      recursive — confirm and record)

### P3 — Retire pyDatalog
- [ ] REQ-KG-016 — `thesis→cozo` projector (thesis-node / sub-argument / invariant)
- [ ] REQ-KG-015 — port `datalog_consistency` D9–D11 to booklogic EDN→Cozo; golden-match
- [ ] REQ-KG-015b — remove the `pyDatalog` dependency and `consistency.dl` (at the gate)

### P5 — Cutover
- [ ] REQ-KG-019 — port the remaining RDF-dataset readers (`query_chapter_evidence`,
      `audit_taxonomy`) to `cozo_store`; golden-match (un-deadlocks the gate)
- [ ] REQ-KG-017 — reconcile the 3 documented RDF↔Cozo divergences; choose canonical
      semantics, update goldens, record decisions:
  - `stale_after_source_refresh`: project_graph's `wasDerivedFrom`(span-URI) vs
    `dateCreated`(bare-manifest-URI) never join → the SPARQL is structurally dead;
    the Cozo port joins on `doc_id` (intended). Fix RDF URI minting or adopt Cozo's.
  - `unsupported_claims`: SPARQL negates `wasDerivedFrom` (span OR `derived_from`);
    the Cozo port negates only the source-span. Decide if `derived_from` counts.
  - project_graph quirks the projector faithfully mirrors: the doubled `wiki/wiki/`
    page-URI prefix; counter-claim `ccStatus` emitted per-record with no
    latest-per-id dedup (open+addressed both present).
- [ ] Flip `KG_BACKEND` default to `cozo`
- [ ] REQ-KG-010/018 — cutover gate test: all fixtures reproduced, no consumer reads/
      writes RDF, no `rdflib`/`pyshacl`/`pyDatalog` import
- [ ] Delete `project_graph` RDF emit, `shapes.ttl`, `.rq` files, `compile_thesis` TTL
      emit; depin `rdflib`/`pyshacl`/`pyDatalog` across book-knowledge/compose/thesis
- [ ] Update README/AGENTS/CLAUDE + docs/operations to the single-graph model

### Phase Z — audit
- [ ] External GPT adversarial audit (audit.md) + two-stage internal review per task

## Phase Z — PR
- [ ] Push + open PR per phase (P0+P1 first).
