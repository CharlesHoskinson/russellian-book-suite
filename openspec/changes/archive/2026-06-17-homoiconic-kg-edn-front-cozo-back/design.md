# Design: homoiconic-kg-edn-front-cozo-back

## Architecture — "EDN front, Cozo back"

One homoiconic **EDN authoring layer** (booklogic, widened from verifier
constraints to the whole KG) is the source of truth: schema, queries, and
constraints are EDN. A **compiler** lowers that EDN to CozoScript. **Cozo**
(already embedded in the verifiers) is the single store/engine. This retires
`rdflib` + SPARQL + SHACL + pyDatalog — three graphs and two Datalog engines
collapse to one. `pycozo` is the Python hot path; the existing `_edn_reader`/
`_edn_writer` bridge handles EDN round-trips. Homoiconicity lives in authoring;
Cozo is a swappable backend (Asami/DataScript is the north star, reachable
because it sits behind the same EDN front).

```
ledger.jsonl ─┐
thesis.yaml ──┼─► projectors ─► Cozo relations ◄─ booklogic EDN ─► CozoScript
graph.json ───┘        (claims, nodes, edges, thesis, communities)   (compiler)
                                   ▲                                    │
                          cozo_store.py (pycozo seam) ◄── compiled queries/constraints
                                   ▲
              book-knowledge / book-thesis / book-compose / book-qa consumers
```

## Components (isolated units; each: what / how-used / depends-on)

1. **`kg-schema.edn`** — the unified graph contract. Entities: `claim`,
   `source-span`, `thesis-node`, `sub-argument`, `wiki-page`, `code-node`,
   `code-edge`, `community`; their attributes and relations. *Used by* the
   projectors (to know relation shapes) and the compiler (to validate references).
   *Depends on* nothing — it is the root contract. Distinct from the JSON-Schema
   record contract, which stays for ledger-write shape.

2. **`booklogic-kg` compiler** — a **pure function** EDN → CozoScript, generalized
   from today's `defquery`/`defconstraint` lowering. *Used by* `cozo_store`.
   *Depends on* `kg-schema.edn` only. Unit-tested EDN-in → CozoScript-out (golden),
   independent of a running store.

3. **`cozo_store.py`** — the one Python↔store seam. Creates relations from
   `kg-schema.edn`, loads projected data, runs compiled queries, returns rows.
   *Used by* every Python consumer. *Depends on* `pycozo` + the compiler. The
   backend-swap boundary: callers see `query(edn) -> rows`, never CozoScript or
   pycozo directly — so Cozo can become Asami later without touching callers.

4. **Projectors** — `ledger→cozo`, `thesis→cozo`, `graph.json→cozo`. Pure
   transforms from existing artifacts to Cozo rows matching `kg-schema.edn`.
   *Used by* a build step. *Depends on* `kg-schema.edn`, `cozo_store`. The
   `ledger→cozo` projector replaces `project_graph`'s RDF emit; `thesis→cozo`
   replaces `compile_thesis`'s TTL emit (both kept in parallel until cutover).

5. **EDN query/constraint library** — the 8 SPARQL queries and the SHACL shapes,
   reauthored as booklogic `defquery`/`defconstraint`. *Used by*
   `run_competency_queries`, `datalog_consistency`, `query_chapter_evidence`, the
   lint gates. *Depends on* the compiler + `cozo_store`.

## Data flow

The append-only JSONL ledger remains the write path (unchanged). A projector
loads the ledger → Cozo `claims`/`source-spans`. `compile_thesis` additionally
emits Cozo `thesis-node`/`supports`. graphify → `graph.json` → loader →
`nodes`/`edges`; god-nodes/communities are recomputed in-engine (Cozo PageRank/
Louvain) so graphify's analysis is reproduced inside the store. Consumers query
Cozo via compiled booklogic. The unification payoff: cross-graph joins —
`code-node ↔ claim`, `claim ↔ thesis ↔ community` — in one store.

## Validation (SHACL replacement)

JSON Schema keeps guarding record shape at ledger-write. SHACL's *semantic*
shapes (the `tbf:status` `sh:in` enum, cardinality, value constraints) become
booklogic `defconstraint` EDN compiled to Cozo `violation[...]` rules — the form
`datalog_consistency` already produces. The status enum becomes one EDN value
that is *both* the schema source and the constraint input, eliminating the
`sh:in`-vs-enum drift. (Prior art: Magic Shapes / recursive-SHACL→Datalog,
cited in the research brief.)

## Interop

`pycozo` (embedded, in-process) is the Python hot path. The existing `_edn_*`
bridge (and babashka if a real EDN round-trip is needed) handles authoring-layer
EDN. `cozo_store` is the single contract-tested seam; no consumer imports
`pycozo` directly, so the backend is swappable.

## Testing — the TDD spine

1. **Characterization fixtures** (golden), frozen on the bermuda workspace before
   any change: the 8 SPARQL result sets, the SHACL conformance/violation reports,
   the D9–D11 defects.
2. **Compiler golden tests**: EDN → CozoScript per construct.
3. **Per-query/shape red→green**: each new Cozo path reproduces its golden; one
   per commit.
4. **graphify loader**: round-trip + recompute-match (god-nodes/communities).
5. **`cozo_store` contract test**: mockable seam; backend-swap safety.
6. **Determinism pin**: byte-identical results across two runs.
7. **Cutover gate** (P5): `rdflib` is deleted only once every characterization
   fixture is reproduced by the new path.

## Risks

- **Cozo maintenance staleness** (no release since Dec 2023). *Mitigation:* the
  EDN-front design makes the backend a compile target — swappable to Asami/
  DataScript without changing authoring or callers (REQ-KG-007).
- **`pycozo` embedded build** on Windows/macOS/Linux CI. *Mitigation:* validate
  `pip install "pycozo[embedded]"` on all three runners in P0 before relying on it.
- **Recursive-SHACL semantics** (some shapes need a documented fixpoint). *Scope:*
  deferred to P2; P0+P1 touch only queries + the enum constraint.

## P0 + P1 boundary (the first plan)

P0: `kg-schema.edn`; the compiler skeleton + golden tests; `cozo_store` over
`pycozo`; the `ledger→cozo` projector; the characterization harness. P1: port the
8 SPARQL queries to booklogic EDN→Cozo, each golden-matched. **No RDF deletion in
P0+P1** — the RDF stack runs in parallel; the harness asserts equivalence.
