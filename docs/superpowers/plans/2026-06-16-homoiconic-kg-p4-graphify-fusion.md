# Homoiconic KG — P4 graphify fusion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Bring graphify's code knowledge graph into the homoiconic Cozo store and prove the headline ability — querying code + claims together in one graph — with a cross-graph **capability/acceptance test** ("a test of the abilities of the skill").

**Architecture:** Extend the existing `book-knowledge` homoiconic store (kg-schema.edn / cozo_store / project_ledger_cozo). A new loader projects graphify `graph.json` into the `code-node`/`code-edge` relations (already declared in `kg-schema.edn`). In-engine Cozo algorithms recompute god-nodes (PageRank) and communities (Louvain) to match graphify's analysis. A `code-claim-link` relation joins code to claims, enabling unified cross-graph queries.

**Tech Stack:** Python 3.13, pycozo (embedded Cozo + graph algorithms), edn_format, pytest. Builds on P0+P1 (PR #251).

---

## File structure

| File | Responsibility |
|---|---|
| `skills/book-knowledge/scripts/project_graphify.py` (new) | `graph.json` → Cozo `code_node`/`code_edge` loader |
| `skills/book-knowledge/scripts/kg_graph_algos.py` (new) | In-engine PageRank (god-nodes) + Louvain (communities) over `code_edge`, written back to `code_node` |
| `skills/book-knowledge/assets/kg-schema.edn` (modify) | Add a `code-claim-link` entity (code-node ↔ claim) if not derivable |
| `skills/book-knowledge/tests/fixtures/graphify-sample.json` (new) | Small deterministic graphify-shaped fixture |
| `skills/book-knowledge/tests/test_project_graphify.py` (new) | Loader + recompute tests |
| `skills/book-knowledge/tests/test_kg_capability.py` (new) | **The cross-graph capability/acceptance test** |

Run tests: `cd skills/book-knowledge && .venv/Scripts/python.exe -m pytest`.

---

## Task P4.1: graphify graph.json → Cozo loader

**Files:** Create `scripts/project_graphify.py`, `tests/fixtures/graphify-sample.json`, `tests/test_project_graphify.py`.

Real graph.json shape (verify against `C:/Users/charl/ProjectLegends/graphify-out/graph.json`): top-level `nodes` (each `{id, label, file_type, source_file, source_location, _origin}`) and `links` (each `{source, target, relation, confidence, weight}`); no precomputed `communities`.

- [ ] **Step 1 (RED):** `test_project_graphify.py::test_loads_nodes_and_edges` — build a small `graphify-sample.json` fixture (≈4 nodes, ≈4 links); `store = CozoStore.in_memory(schema_path=...)`; `project_graphify(graph_json_path, store)`; assert `store.query_edn('(defquery :n :find [?id] :where [[?c :code-node/id ?id]])')` returns the fixture's node ids, and an analogous code-edge query returns the edges. Run — expect FAIL.
- [ ] **Step 2 (GREEN):** implement `project_graphify(path, store)`: read graph.json, map each node → a `code_node` row (`id`, `label`; `rank`/`community` left null until P4.2), each link → a `code_edge` row (`source-id`, `target-id`, `relationship`=`relation`, `weight`). Use `store.load("code-node", ...)`/`store.load("code-edge", ...)`. Deterministic order.
- [ ] **Step 3:** run; full `tests/ -q` green. Commit `kg(P4.1): graphify graph.json -> Cozo code-node/code-edge loader`.

## Task P4.2: in-engine god-nodes + communities

**Files:** Create `scripts/kg_graph_algos.py`; extend `tests/test_project_graphify.py`.

- [ ] **Step 1 (RED):** `test_recompute_godnodes_and_communities` — on a fixture whose most-connected node is known, after `recompute_code_graph(store)` assert the top-ranked `code_node` (god-node) is that node and that community ids are assigned (nodes in a connected cluster share a community). Run — expect FAIL.
- [ ] **Step 2 (GREEN):** implement `recompute_code_graph(store)` running Cozo PageRank + Louvain over `code_edge`. **Pin the exact Cozo invocation by running it against a live store** (the naive `<~ PageRank(*n[id], *e[fr,to])` form errors with "cannot be interpreted as an edge"; find the correct edge-relation argument form, e.g. passing only the edge relation, in the Cozo algorithms docs). Write `rank`/`community` back into `code_node` (update rows). Document the invocation.
- [ ] **Step 3:** run; full suite green. Commit `kg(P4.2): in-engine PageRank god-nodes + Louvain communities`.

## Task P4.3: cross-graph capability/acceptance test (the deliverable)

**Files:** Modify `assets/kg-schema.edn` (add `code-claim-link {:attrs [:id :code-id :claim-id] :relations [[:of-code :code-node] [:of-claim :claim]]}`; update `EXPECTED_ENTITIES` in `test_kg_schema.py`); Create `tests/test_kg_capability.py`.

This is the **test of the abilities of the skill** — it must demonstrate something the RDF/SPARQL path could not: code graph and claims graph queried together in ONE store.

- [ ] **Step 1 (RED):** `test_kg_capability.py::test_code_and_claims_unified_query` — in one `CozoStore`: `project_ledger` (claims), `project_graphify` (code), `recompute_code_graph` (god-nodes/communities), and load a few `code-claim-link` rows (code module ↔ the claim it supports). Then run a UNIFIED `query_edn` that spans both graphs, e.g. *"for each god-node code module, the verified claims linked to it"* (join `code-node` (top rank) → `code-claim-link` → `claim` status verified). Assert it returns the expected (code, claim) pairs. Run — expect FAIL.
- [ ] **Step 2 (GREEN):** add the `code-claim-link` entity to the schema + a small loader (or inline rows for the test); author the unified EDN query; iterate against the live store until it returns the expected cross-graph rows. (Production code↔claim link *semantics* — how links are derived from real data — is noted as a follow-on; the capability test uses an explicit link relation to prove the join works.)
- [ ] **Step 3:** add `test_godnode_communities_match_graphify` if a real `graph.json` is available (best-effort/skip if absent). Run; full suite green. Commit `kg(P4.3): cross-graph code<->claim capability test + code-claim-link`.

## Task P4.4: optional CLI surface

- [ ] Add a `forge`/script entry or `run_competency_queries`-style hook to run a graphify projection + a sample cross-graph query end-to-end, so the ability is runnable, not just tested. Commit. (Skip if it grows beyond a thin wrapper.)

---

## Self-review
- Spec coverage: P4 implements the umbrella change's P4 task list (graph.json loader, in-engine recompute, code↔claim joins). REQ-KG-006-style golden equivalence does not apply (no SPARQL original for the code graph); correctness is by the capability test + recompute-match.
- The capability test (P4.3) is the explicit "test of the abilities of the skill."
- Follow-on (note, don't build): production semantics for the code↔claim link (derive from claim source files / symbol references); P2/P3/P5 unchanged.
