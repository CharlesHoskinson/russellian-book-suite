# Research brief — a homoiconic knowledge graph (graphify + Clojure)

**Date:** 2026-06-16. Informs `openspec/changes/homoiconic-kg-edn-front-cozo-back/`.

## Grounding: three half-bridged graphs, two Datalog engines

- **RDF claims graph** — `rdflib`, TriG, SPARQL competency queries
  (`run_competency_queries.py`), SHACL `shapes.ttl` (the `sh:in` list mirrors the
  JSON-Schema `tbf:status` enum and can drift).
- **Ad-hoc Datalog** — `datalog_consistency.py` already loads the Turtle into
  **pyDatalog** and runs `consistency.dl` for D9–D11. RDF→Datalog is already
  bridged by hand.
- **booklogic** — a Clojure/EDN DSL compiled via nbb, emitting
  `defquery`/`defconstraint`.
- **Cozo, embedded** — the Rust verifiers run booklogic-emitted Datalog via the
  `cozo` crate (`kg.rs`).
- **EDN bridge already exists** — `_edn_reader.py`/`_edn_writer.py`;
  `export_symbolic_trace.py` already serialises the ledger to EDN.

"Homoiconic KG" is therefore a **consolidation** play, not a greenfield build.

## What "homoiconic" means here

The EDN-Datalog family makes schema, data, rules, and queries the *same* EDN data
structure: a query is an EDN vector, a rule is EDN, a transaction is EDN. Over an
application-controlled (non-web-federated) graph this beats RDF/SPARQL because
queries compose as data (no second grammar, no string interpolation), and Datalog
subsumes SPARQL (recursion) under a closed-world assumption — the right default
for a curated claim ledger.

## Substrate comparison

| Substrate | Query=EDN | Homoiconic | Embeddable | Python | In-engine graph algos | Status |
|---|---|---|---|---|---|---|
| Cozo | no (CozoScript) | no | yes | yes (`pycozo`) | yes (PageRank/Louvain/Dijkstra) | stalled (v0.7.6, 2023-12) |
| Datomic | yes | yes | yes | no (REST only) | no | active |
| DataScript | yes | yes | yes (in-mem) | no (JS) | no | active (2025) |
| Asami + naga | yes (+EDN rules) | yes (rules-as-EDN first-class) | yes | JVM only | partial | quiet (2023) |
| XTDB v2 | XTQL EDN-shaped | partial | server | SQL/PG | no | active (GA 2025) |
| Fluree | no (JSON-LD) | no | yes | community | OWL/SHACL | active |

Central tension: the EDN-homoiconic stores are JVM-bound (weak Python); the
Python-native one (Cozo) is not EDN-homoiconic. No tool maxes all three.

## Bridging the existing assets

- **RDF → datoms** is a clean, documented mapping (Subject/Predicate/Object →
  Entity/Attribute/Value; datoms add time + retraction, subsuming the append-only
  ledger). Tooling: Kiara (Turtle→datom), clj-tparse (Turtle→EDN).
- **SHACL → Datalog** is established prior art, not a downgrade: a shape becomes a
  Datalog rule whose head is a `violation` predicate (Magic Shapes, VLDB'22;
  recursive-SHACL semantics, ISWC'18). The `sh:in` enum becomes a `not
  valid-status[s]` rule over enum-as-data.
- **graphify `graph.json`** (nodes/edges/communities; god-nodes = most-connected;
  Leiden communities — same algorithm as Microsoft GraphRAG) → two Cozo relations;
  god-nodes/communities recomputable in-engine. Prior art for code+domain in one
  Datalog store: Datomic codeq, Meta Glean, jQAssistant.

## Interop

`pycozo` (pure Python, in-process Rust Datalog) is the lowest-friction hot path;
the existing `_edn_*` bridge (and babashka EDN-over-stdio if a real EDN round-trip
is needed) covers the authoring layer. libpython-clj / JVM-in-Python are the wrong
direction for a Python-primary repo.

## Decision

**Pattern C — EDN front, Cozo back** (recommended), with **Pattern B —
Asami/DataScript pure-EDN store** as the north star. Pattern C widens booklogic
(already EDN→Cozo) from verifier constraints to the whole KG; gets homoiconicity
where it matters (authoring/composition/inspection) while keeping Cozo's
embeddability, speed, in-engine graph algos, and Python interop; collapses two
Datalog engines to one; and keeps the backend swappable to Asami later because it
is a compile target. Main risk: Cozo staleness — mitigated by the swappable-backend
seam. See the change's `design.md`.

## Citations

Datomic query-as-data: docs.datomic.com/query/query-data-reference.html ·
docs.datomic.com/reference/edn.html · blog.datomic.com/2015/01/datalog-enhancements.html.
Substrates: blog.datomic.com/2023/04/datomic-is-free.html · github.com/tonsky/datascript ·
github.com/quoll/asami · github.com/quoll/naga · xtdb.com/blog/launching-xtdb-v2 ·
github.com/cozodb/cozo · github.com/fluree/db.
RDF↔datom + SHACL→Datalog: github.com/quoll/kiara · www.infoq.com/articles/Datomic-Information-Model/ ·
www.vldb.org/pvldb/vol15/p2284-ahmetaj.pdf (Magic Shapes) ·
link.springer.com/chapter/10.1007/978-3-030-00671-6_19 (recursive SHACL).
Code+domain KG: blog.datomic.com/2012/10/codeq.html · glean.software/docs/databases/ ·
arxiv.org/abs/2404.16130 (GraphRAG) · pypi.org/project/graphifyy/ ·
docs.cozodb.org/en/latest/algorithms.html.
Interop: github.com/cozodb/pycozo · babashka.org · github.com/babashka/pods.

Spot-check before citing as fact: "XTDB v2 dropped EDN Datalog" (inferred from v2
framing XTQL as the replacement, not an explicit removal statement); Cozo/pycozo
maintenance staleness (no release since 2023-12) — the chief risk to Pattern C.
