# Design: tier3-cozo-runtime

## Choice of Cozo integration shape

Two candidates were considered:

- **(a) Rust `cozo` crate invoked from `kg.rs`.** Already a
  declared optional dependency (`cozo = "0.7"`, gated on the
  `kg` feature) in both verifier Cargo.toml files. The bermuda
  verifier already wires `cozo::DbInstance::new("mem", ...)`
  and runs scripts inside `kg.rs::ingest_and_summarize`. The
  surface to promote is just "make sure `npm run build` calls
  into this module and routes its output to the verdict".
- (b) External `cozo` CLI driven by `npm run build`. Adds a
  shell dependency and forces EDN-to-Datalog text serialisation
  at every smoke run. Loses the in-process embedding.

**Decision: (a).** The bermuda `kg.rs` already wires the
correct path; the gap is in the orchestrator (`smt.rs` / `main.rs`
calling into `kg::ingest_and_summarize`) and in the verdict
shape.

## Query-result EDN shape

`work/query-results.edn` is written per-run by the Rust verifier:

```edn
{:version 1
 :queries
  {:Q001-orphan-claims    [{:claim "C042"} {:claim "C108"}]
   :Q002-low-confidence   [{:claim "C014" :score 0.32}]
   :Q003-chapter-coverage []}}
```

Empty-row queries SHALL still appear (with `[]`) so downstream
consumers can distinguish "query ran and produced nothing"
from "query was never registered".

## Combined verdict shape

The verdict's previous shape was the Z3 result alone. The new
combined shape:

```edn
{:status      :unsat            ; max of Z3 status and Cozo status
 :z3-unsat-core [...]            ; existing field, unchanged
 :queries     [:Q002-low-confidence :Q003-chapter-coverage]
 :cozo-defects
   {:Q002-low-confidence
     [{:claim "C014" :score 0.32 :severity :warn}]}
 :remedy-bindings
   {:W001-flag-claim
     {:rows [{:claim "C014"}]}}
 :warnings    [{:phase :datalog :reason :datalog-timeout
                :query :Q005-slow-query :elapsed-ms 10042}]}
```

The `:status` field becomes the worst-case of Z3's status and
Cozo's status (`:unsat` if any Cozo defect was emitted with
severity `:fatal` or any constraint produced `:unsat`).

## Remedy binding

A `defremedy` form whose `:when` clause references a query
name receives the query's full row vector as the binding:

```edn
(defremedy W001-flag-claim
  :when   {:query :Q002-low-confidence}
  :propose {:action :annotate
            :rows-from-query? true})
```

At verdict time the framework materialises
`:remedy-bindings :W001-flag-claim :rows` = `[{:claim "C014" ...}]`
so the downstream `book-qa` tool can drive the annotation
action over the actual rows.

## Timeout handling

`VERIFIER_DATALOG_TIMEOUT_MS` (default 10000) wraps each Cozo
script invocation in a `tokio::time::timeout` (or `std::thread`
join with timeout) and yields a `:datalog-timeout` warning on
the verdict's `:warnings` list. The verdict still reports for
the other queries; one slow query SHALL NOT block the rest.

## SUPPORT_MATRIX update

Three row edits:

```
| `defrule`                      | wired        | `rules_for_egg.rs`  | egg          | wired              |
| `defconstraint :backend :cozo` | wired        | `codegen_axioms.py` | Cozo         | wired              |
| `defquery`                     | wired        | `codegen_kg.py`     | Cozo         | wired              |
| `defremedy`                    | wired        | `codegen_remedy.py` | n/a          | wired (query-bound)|
```

The "wired-builder" legend entry is retired; the "external"
entry shrinks to "purely declarative remedies whose `:when`
clause does NOT reference a `defquery`".

## Why not Tier 4 (full multi-solver verdict)?

Tier 4 generalises `:status` into a per-backend tuple
(`{:z3 :sat :cozo :unsat :egg :proved}`) and lets each surface
its own defects through a uniform schema. Tier 3 stops at
"Cozo's verdict influences the unified `:status` and Cozo's
rows show up alongside Z3's unsat core". The narrower scope
keeps the verdict shape additive (adds `:queries`,
`:cozo-defects`, `:remedy-bindings`) without changing the
meaning of `:status` beyond a worst-case rollup.
