# Change: homoiconic-kg-edn-front-cozo-back

**Date:** 2026-06-16
**Branch:** `feat/homoiconic-kg`
**Capability:** `homoiconic-kg` (new)
**Design:** `design.md` (this change). Research brief informing it:
`docs/superpowers/research/2026-06-16-homoiconic-kg-research.md`.

## Why

The suite has **three half-bridged knowledge graphs** — the RDF claims graph
(`rdflib`, TriG, SPARQL, SHACL), the embedded **Cozo** verifier graph
(`kg.rs`), and the external **graphify** code graph (`graph.json`) — and **two
Datalog engines** (pyDatalog in `book-thesis/scripts/datalog_consistency.py` and
Cozo in the verifiers), with a hand-rolled RDF→Datalog step in between. Queries
are strings in two grammars (SPARQL, `.dl`); the `sh:in` enum drifts from the
JSON-Schema enum (a documented foot-gun); and the code graph never joins the
domain graph.

`booklogic` is already an EDN DSL that compiles to Cozo Datalog. Widening it from
"verifier constraints" to the **whole** knowledge graph consolidates all three
graphs into one homoiconic-front, Cozo-backed store: schema, queries, and
constraints are authored as EDN (code = data = query), compiled to one engine.

## What

Adopt **"EDN front, Cozo back"** (research Pattern C; Pattern B — a pure-EDN
store via Asami/DataScript — is the stated north star, reachable later because
the backend is a compile target):

1. Define the unified graph schema as one EDN document (`kg-schema.edn`).
2. Generalize the booklogic→Cozo compiler from verifier constraints to KG
   queries + constraints + graph-loads.
3. Stand up a single Cozo store accessed from Python via `pycozo` behind one seam
   module, retiring `rdflib`/SPARQL/SHACL/pyDatalog at cutover.
4. Project the claim ledger, thesis, and graphify `graph.json` into Cozo
   relations; expose cross-graph joins (code ↔ claim ↔ thesis).
5. Re-express SHACL semantic shapes and the D9–D11 consistency rules as booklogic
   EDN constraints. Keep JSON Schema as the record-shape contract.

Migration is a **test-guarded big-bang**: characterization golden fixtures freeze
current RDF/SPARQL/SHACL/pyDatalog behaviour first; every ported query/shape must
reproduce its golden before the RDF stack is deleted.

## Scope (this change is the umbrella; work is sequenced P0–P5)

- **P0** Cozo store + `pycozo` seam + `kg-schema.edn` + ledger→Cozo projector
  (runs parallel to RDF; characterization harness compares both). *First plan.*
- **P1** Port the 8 SPARQL queries to booklogic EDN→Cozo (golden-matched). *First plan.*
- **P2** SHACL → EDN constraints; replace `validate_shacl`.
- **P3** Port `datalog_consistency` (pyDatalog) → booklogic EDN→Cozo; retire pyDatalog.
- **P4** graphify fusion — loader + code↔claim joins + in-engine recompute.
- **P5** Cutover — delete `rdflib`/SPARQL/SHACL; Cozo sole store.

The first implementation plan covers **P0 + P1**. P2–P5 are follow-on specs.

## Requirements

See `specs/homoiconic-kg/spec.md` (EARS). Summary:

| REQ id | One-line |
|---|---|
| REQ-KG-001 | Unified graph schema authored as one EDN document (8 entities) |
| REQ-KG-002 | Single Cozo store behind one Python (`pycozo`) seam (`query`/`load`) |
| REQ-KG-002b | No module other than the seam imports `pycozo`/emits CozoScript |
| REQ-KG-003 | Pure EDN→CozoScript compiler (byte-identical, no store I/O) |
| REQ-KG-004 | Ledger projects latest-per-id verified claims into Cozo; ledger untouched |
| REQ-KG-005 | Characterization golden fixtures committed before each port lands |
| REQ-KG-006 | Each of the 8 SPARQL queries reproduced (result-set equal) via EDN→Cozo |
| REQ-KG-007 | Backend swappable behind the seam without changing consumers |
| REQ-KG-008 | Deterministic: byte-identical relations + canonically-ordered result sets |
| REQ-KG-009 | Status enum is a single EDN source feeding schema and constraint |
| REQ-KG-009b | No second independently-edited copy of the status enum |
| REQ-KG-010 | RDF stack removed only after every characterization fixture is reproduced |
| REQ-KG-011 | Store relations are created from, and conform to, `kg-schema.edn` |

## Out of scope (this change)

- P2–P5 detail (own specs): SHACL-port semantics, pyDatalog retirement, graphify
  fusion joins, final cutover deletions.
- Store-level homoiconicity (Pattern B / Asami) — the north star, not day one.
- Changing the append-only JSONL ledger write path or the JSON-Schema record
  contract.
- The SMT (z3) verifier path — unchanged; only the Datalog/graph layer moves.

## Acceptance (P0 + P1)

- `kg-schema.edn` exists and the booklogic→CozoScript compiler has golden unit
  tests (EDN in → CozoScript out).
- The ledger→Cozo projector loads the bermuda workspace; `cozo_store` round-trips
  via `pycozo`.
- All 8 competency/coverage/defeasible queries run as booklogic EDN→Cozo and
  reproduce their characterization golden fixtures.
- The seam has a contract test; results are deterministic across two runs.
- RDF/SPARQL remain in place (parallel) — no deletion in P0+P1.
