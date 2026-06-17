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

## P2 — SHACL → EDN constraints (follow-on spec)
- [ ] REQ-KG-009 — status enum single EDN source feeding schema + constraint
- [ ] Port each SHACL shape to a booklogic `defconstraint`; replace `validate_shacl`
- [ ] Recursive-SHACL shapes: choose + document a fixpoint semantics

## P3 — Retire pyDatalog (follow-on spec)
- [ ] Port `datalog_consistency` D9–D11 from pyDatalog to booklogic EDN→Cozo
- [ ] Remove the `pyDatalog` dependency and `consistency.dl`

## P4 — graphify fusion (follow-on spec)
- [ ] `graph.json` → EDN → Cozo `nodes`/`edges` loader (round-trip test)
- [ ] Recompute god-nodes/communities in-engine (PageRank/Louvain) — match graphify
- [ ] Cross-graph joins: code-node ↔ claim ↔ thesis; example queries + tests

## P5 — Cutover (follow-on spec)
- [ ] REQ-KG-010 — cutover gate: all characterization fixtures reproduced
- [ ] Delete `rdflib`/SPARQL/SHACL/`project_graph` RDF emit; Cozo sole store
- [ ] Update README/AGENTS/CLAUDE + docs/operations to the single-graph model
- [ ] Reconcile RDF↔Cozo divergences surfaced during P1 (documented inline in the
      kg-queries EDN), deciding the canonical semantics for each:
  - `stale_after_source_refresh`: project_graph's `wasDerivedFrom`(span-URI) vs
    `dateCreated`(bare-manifest-URI) never join → the SPARQL is structurally dead;
    the Cozo port joins on `doc_id` (intended). Fix RDF URI minting or adopt Cozo's.
  - `unsupported_claims`: SPARQL negates `wasDerivedFrom` (span OR `derived_from`);
    the Cozo port negates only the source-span. Decide if `derived_from` counts.
  - project_graph quirks the projector faithfully mirrors: the doubled `wiki/wiki/`
    page-URI prefix; counter-claim `ccStatus` emitted per-record with no
    latest-per-id dedup (open+addressed both present).

## Phase Z — PR
- [ ] Push + open PR per phase (P0+P1 first).
