# Design: tier3-egg-promotion

## Choice of rewrite engine

Three candidates were considered:

- **(a) `egg` crate (Rust egraph library).** Already a declared
  optional dependency (`egg = "0.10"`, gated on the `eqsat`
  feature). Industry-standard equality saturation. The
  `egg::Runner`, `egg::Rewrite`, and `egg::Extractor` APIs map
  one-to-one onto the BookLogic `defrule` surface. The `prove`
  pattern via `egraph.equivs(...)` is documented.
- (b) Datafrog-style Datalog rewriter. Would require encoding
  rewrites as Horn clauses; loses canonical-form extraction
  semantics; reuses the Cozo stack but for a job it is not
  designed for.
- (c) Hand-rolled rewrite engine. Reinvents `egg`; no congruence
  closure; no extraction; no termination guarantees.

**Decision: (a).** The dependency is already vendored; the
`egg-rs` API matches the abstraction the DSL already exposes.

## EGraph node-type design

One e-class node kind per BookLogic atom kind, expressed as a
single `egg::define_language!` enum:

```rust
egg::define_language! {
    enum BookLogicLang {
        // primitives
        Num(f64),
        Sym(egg::Symbol),

        // arithmetic
        "+" = Add([Id; 2]),
        "-" = Sub([Id; 2]),
        "*" = Mul([Id; 2]),
        "/" = Div([Id; 2]),

        // logical
        "and" = And(Vec<Id>),
        "or"  = Or(Vec<Id>),
        "not" = Not(Id),

        // comparison
        "<"   = Lt([Id; 2]),
        "<="  = Le([Id; 2]),
        "="   = Eq([Id; 2]),

        // predicate application (head + N args)
        "app" = App(Vec<Id>),
    }
}
```

A BookLogic predicate `(:osmotic-pressure-pa ?s)` becomes
`(app osmotic-pressure-pa ?s)`. Free vars `?a` / `?b` become
`egg::Var`s. The flat `App` form keeps the language enum small
and lets `defrule` `:lhs` / `:rhs` patterns compile to
`egg::Pattern<BookLogicLang>` via `parse()`.

## Compilation flow

1. **Read rules.** `codegen_axioms.py` reads
   `rules/booklogic/rules.edn` and emits a generated
   `rules_for_egg.rs` containing the `egg::rewrite!` macro
   invocations for each `defrule`.
2. **Saturate per constraint.** For each `defconstraint`, the
   codegen emits a call to `eqsat::canonicalise(&expr)` that
   instantiates a `Runner`, runs saturation, and extracts the
   cost-minimal form via `egg::Extractor::new(&egraph,
   AstSize)`.
3. **Hand the canonical form to Z3.** The Z3 assertion is built
   from the extracted form, not the surface form. The unsat-core
   reporter records both surface and canonical IDs so authors
   can debug.
4. **`:backend :egg`.** A `(defconstraint ... :backend :egg ...)`
   form does not flow to Z3; instead it generates a call to
   `eqsat::prove_equiv(lhs, rhs)` which returns `:proved` (egg
   saw the two terms in the same e-class within budget),
   `:not-proved` (timed out), or `:disproved` (the rule set is
   inconsistent, surfaced as a defect).

## Saturation budget

Equality saturation can diverge on rules like
`?x -> (* ?x 1)`. `egg::Runner` exposes `with_node_limit`,
`with_iter_limit`, and `with_time_limit`. The framework picks:

- Default node limit: **10000**, override
  `VERIFIER_EQSAT_NODE_LIMIT` env var.
- Default iter limit: **30**, override
  `VERIFIER_EQSAT_ITER_LIMIT`.
- Default time limit: **5s**, override
  `VERIFIER_EQSAT_TIMEOUT_MS`.

When any limit fires, the run returns `StopReason::NodeLimit`
(or analogous); the framework surfaces a
`{:phase :eqsat :reason :budget-exceeded :rule "R042-..."}`
warning to the verdict's `:warnings` field. The constraint is
still asserted with the BEST canonical form found before the
budget fired — not silently dropped.

## SUPPORT_MATRIX update

Two row edits:

```
| `defrule`                    | wired        | `rules_for_egg.rs`  | egg          | wired  |
| `defconstraint :backend :egg`| wired        | `eqsat.rs::prove`   | egg          | wired  |
```

The legend's "stub" and "DROP" sections shrink correspondingly;
the "Roadmap pointers" section drops the Tier 3 line.

## Test surface

A new file
`verifiers/osmotic_pressure/rust-verifier/tests/eqsat_canonical.rs`
loads a 3-rule fixture (commutativity, associativity, identity
for `*`) and asserts that `(* M (* 1 i))`, `(* i M)`, and
`(* i (* M 1))` all extract to the same canonical form. A
sibling test `eqsat_budget.rs` loads a deliberately divergent
rule (`?x -> (* ?x 1)`) and asserts the run returns with
`StopReason::NodeLimit` AND a `:warnings` entry mentioning the
rule ID.

## Why not Tier 4 (full multi-solver verdict)?

Tier 4 lifts egg from "post-saturation feeder for Z3" to "peer
solver returning its own sat/unsat verdict merged with Z3's".
That is the next iteration. Tier 3 stops at canonicalisation
plus prove-equiv — enough to retire the `:egg` DROP row without
expanding the verdict shape.
