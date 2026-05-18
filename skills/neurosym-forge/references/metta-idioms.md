# metta-idioms

REQ-BOOKLOGIC-044. What this framework borrows from MeTTa, what it
deliberately does NOT borrow, and which backend handles which job.

The BookLogic DSL is shaped by MeTTa (the Hyperon meta-type-theory
language) but is not a MeTTa implementation. This document marks the
borders precisely so authors know where the analogy ends.

## 1. MeTTa concepts the framework borrows

### 1.1 Atomspace

In MeTTa, an "atomspace" is a graph of atoms — symbols, variables,
expressions, and grounded values — over which match-and-rewrite
operations run. Atoms are the data; rules are also atoms.

In this framework, the atom stream is EDN-on-disk. Each atom is a map
with `:id`, `:kind`, and kind-specific fields (see
`references/atomspace-edn.md`). The atomspace is `work/claims.edn`
plus the project's `rules/booklogic/*.edn`. There is no live in-memory
atomspace shared across phases — every boundary is a serialised EDN
file. That makes the substrate auditable but gives up some of MeTTa's
runtime expressiveness.

The borrowed idea: atoms-as-data, with rules and facts in the same
representational space.

### 1.2 Grounded atoms

MeTTa distinguishes "grounded" atoms — those whose value is a
native host-language object — from purely symbolic atoms. A grounded
atom's value can be inspected at evaluation time, used in arithmetic,
or passed to a host function.

This framework's `:expression` atoms with `:value` carrying an
`Edn::Double`, `Edn::Int`, `Edn::Bool`, or `Edn::Str` are direct
analogues. The `parse-float` and `parse-int` helpers in `deflift`
produce them; `smt.rs` consumes them when emitting Z3 axioms.

The borrowed idea: a typed native value can ride inside an atom.

### 1.3 Rewrite rules

MeTTa's `(= LHS RHS)` equational rules drive its evaluator: any
expression matching `LHS` rewrites to `RHS`. Equations are also atoms
in the atomspace.

`defrule` mirrors this — `:lhs` and `:rhs` patterns. The intent is
egg-backed equality saturation (see `references/rewrite-rule-style.md`),
which is a strict-superset of single-step rewriting and a closer
analogue to MeTTa's open evaluator than naive substitution.

The borrowed idea: rules are data, written in the same surface
language as the facts they manipulate.

## 2. MeTTa concepts the framework does NOT borrow

### 2.1 Full unification

MeTTa's evaluator runs full unification — matching one structure
against another with two-way variable substitution. That gives
powerful but expensive search semantics.

This framework uses match-only via `meander.epsilon`: the LHS is a
pattern, the data is concrete, and bindings flow one direction. No
unifier crawls the e-graph at runtime. The Tier 3 egg integration
will give one-step term unification within an e-class, but the
arbitrary deep unification of MeTTa is out of scope.

### 2.2 Dynamic dispatch on atom shape

MeTTa atoms can carry arbitrary structure and the evaluator dispatches
on shape at runtime. New atom shapes can appear without a schema
update.

This framework types atoms at compile time. `defpredicate` declares
the arity and value-sort of every predicate that may appear in the
atom stream; `defsort` declares the universe of sort names. The Rust
verifier dispatches on `:kind` (a closed set of three) and
`:predicate` (a closed set declared per project). Phase C's
`booklogic-schema.edn` enforces this closed-world view at the
EDN-level.

The trade-off: less expressive than MeTTa's open evaluator, but
auditable and Z3-friendly.

### 2.3 MeTTa's dependent type system

MeTTa's gradual dependent type system can express types like "even
integer" or "list of length n", and the evaluator can refine types
during reduction.

This framework uses a flat Quint-style sort lattice. The sorts in
v1 are `:int`, `:real`, `:bool`, `:string`, plus domain-specific
sorts like `:solution`. Sorts do not depend on values. Refinement
predicates (the "even" / "positive" / "in-range" checks) live in
`defconstraint` forms, not in the type system.

The trade-off: simpler reasoning at the cost of expressiveness.

### 2.4 Top-level evaluation directive `!`

In MeTTa, `!` is a top-level directive: prefixing an atom with `!`
causes immediate evaluation rather than insertion into the
atomspace. There is no equivalent in this framework — every atom
goes through the same pipeline; nothing is "evaluated now" outside
the standard phase progression.

## 3. Cross-references: which backend handles what

The framework supports three constraint backends (see
`SUPPORT_MATRIX.md` for live/stub status):

- `:z3` — the live path. Arithmetic-shaped constraints
  (`approx=`, `<`, `<=`, `=`, `*`, `+`, `-`). Codegen runs through
  `skills/neurosym-forge/scripts/codegen_axioms.py` to emit
  `rust-verifier/src/axioms.rs`. Tracker names equal constraint
  ids; on `:unsat`, the core names the offending claim.
- `:egg` — STUB. Intended for canonical-form rewrites consumed by
  an `egg::Runner` in `rust-verifier/src/eqsat.rs`. Today
  `codegen_axioms` silently drops `:egg`-backed constraints
  (cf. `references/rewrite-rule-style.md` § 3). Tier 3 makes it
  live.
- `:cozo` — STUB. Intended for entity-relationship Datalog queries
  via `rust-verifier/src/kg.rs`. Today the same dropping behaviour
  applies. The Cozo store is wired in `add_grounded_atom.py` but
  the constraint codegen path is not.

The CLJS substitution layer (`cljs-orchestrator/src/main/<slug>/phases.cljs`)
is where rules in `rules.edn` are consumed today — independent of the
three constraint backends.

## 4. When to use each backend

Recipe by problem shape:

- **Arithmetic identities, tolerance checks, simple linear or
  polynomial relations.** Use `:z3`. The osmotic-pressure verifier's
  van 't Hoff constraint is a canonical example.
- **Canonical algebraic form before assertion.** Use `:egg` (when
  live). Write the rules as `defrule`. Today, hand-canonicalise the
  constraint and use `:z3`.
- **Entity-relationship queries, graph reachability, transitive
  closures.** Use `:cozo` (when live). Today, encode the relation
  as a `:z3` axiom or do the query in Python.
- **Match-and-substitute on the atom stream itself.** Use the CLJS
  rewrite pass (`phases.cljs` + `rules.edn`). This is live but
  shallow — single-pass meander rewrites, not equality saturation.

## 5. Form-by-form analogy table

A concise summary of how MeTTa's surface forms map (or fail to map)
onto BookLogic forms:

| MeTTa | BookLogic | Notes |
| --- | --- | --- |
| `(= LHS RHS)` | `(defrule R### :lhs ... :rhs ...)` | Stub today; egg backend is the Tier 3 target. |
| `(: x T)` | `(defpredicate :x [arg-sorts] :ret-sort)` plus `(defsort :T)` | Flat sort lattice, no dependent types. |
| `!` (top-level eval) | (no equivalent) | Every atom goes through the standard phase pipeline; no inline force-eval. |
| `(match $space pat tmpl)` | meander rewrite in `phases.cljs` plus Cozo Datalog queries (stub) | One-pass match; no full unification. |
| `(superpose (a b c))` | (no equivalent in v1) | Non-determinism is unrealised. |
| `(collapse expr)` | (no equivalent in v1) | Branching reification is unrealised. |
| Grounded atoms | `:expression` atoms with native `:value` | Direct analogue; `parse-float` / `parse-int` produce them. |
| Self-reflection (`add-atom`, `get-atoms`) | Build-time `add_*` helpers only | Restricted, helper-mediated, checksummed. |

This table is the canonical "is this idiom available?" lookup. A row
without a BookLogic entry is genuinely absent, not just renamed.

## 6. What "we don't borrow" buys us

The omissions are deliberate. They buy three properties:

- **Decidability.** Without full unification, the rewrite layer is
  guaranteed to terminate. Z3 stays the only source of search.
- **Auditability.** Every atom is typed and every boundary is an EDN
  file on disk. There is no hidden in-memory atomspace whose state
  changes between phases.
- **Tool compatibility.** Closed-world predicate dispatch is what
  makes Z3 axiom codegen tractable. Open-world dispatch would force
  runtime introspection and rule out static `assert_and_track`
  emission.

The borrowed concepts — atomspace-as-data, grounded values, rule
forms — give us the readable surface. The omitted concepts —
unification, non-determinism, runtime reflection — would give
expressiveness we cannot yet verify.

## See also

- `references/atomspace-edn.md` — the atom shape that materialises
  MeTTa's "atomspace" idea.
- `references/grounded-atoms.md` — the deflift pass that produces
  MeTTa-style grounded atoms.
- `references/rewrite-rule-style.md` — `defrule` conventions and
  the egg stub story.
- `SUPPORT_MATRIX.md` — live/stub table for the three backends.
- `verifiers/osmotic_pressure/cljs-orchestrator/src/main/osmotic_pressure/phases.cljs`
  — where the substitution layer lives.
- `skills/neurosym-forge/scripts/codegen_axioms.py` — the `:z3` path.
