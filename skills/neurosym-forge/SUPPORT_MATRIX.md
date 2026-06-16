# BookLogic v0.4 Support Matrix

> Single source of truth for which DSL form / backend combinations are
> actually wired vs claimed. Drift from `codegen_axioms.py` is caught
> by `tests/test_support_matrix.py` (REQ-BOOKLOGIC-049, 050).

## Form-family matrix

| Form family                  | CLJS compile | Codegen path        | Solver       | Status |
|------------------------------|--------------|---------------------|--------------|--------|
| `defsort`                    | wired        | (validation only)   | n/a          | wired  |
| `defpredicate`               | wired        | (validation only)   | n/a          | wired  |
| `deflift`                    | wired        | `predicates.edn`    | n/a          | wired  |
| `deflift :backend :llm`      | wired (alpha) | `scripts/_llm_lift.py` | LLM       | wired (alpha) |
| `defrule`                    | wired        | `eqsat.rs::make_rewrites` | egg     | wired  |
| `defconstraint :backend :z3` | wired        | `codegen_axioms.py` | Z3           | wired  |
| `defconstraint :backend :egg`| wired        | `eqsat.rs::prove_equiv` | egg      | wired  |
| `defconstraint :backend :cozo` | wired      | `kg.rs::evaluate_constraint` | Cozo | wired  |
| `defconstraint :scope :subject` | wired      | `codegen_axioms.py` (`axioms_for_subject`) | Z3 | wired  |
| `defconstraint :scope :corpus` | wired      | `codegen_axioms.py` (`axioms_corpus`) | Z3 | wired  |
| `defquery`                   | wired        | `kg.rs::run_queries` | Cozo        | wired  |
| `defremedy`                  | wired        | `verdict_to_qa.py`  | n/a          | wired (query-bound) |
| `defconstraint :assert (and / or / not / =>)` | wired | `codegen_axioms.py` | Z3      | **wired (v0.5)** |
| `defconstraint :assert (forall / exists)`     | wired | `codegen_axioms.py` | Z3      | **wired (v0.6)** |

## Status legend

**wired** — Full end-to-end path: CLJS expand → codegen → solver/runtime → verdict surface.
A defconstraint :backend :z3 form is asserted in Z3, included in unsat-core
reporting, and surfaces as a defect entry in `verification-defects.json`.

**stub** — The form is recognised by the CLJS expander and stored in the
intermediate registry, but no downstream codegen consumes it. Adding the form
is a no-op at solver time. (Phase H + I of the Tier 2-4 plan retired the last
remaining stub rows; this entry is retained for any form that lands in this
state in the future.)

**DROP** — The form is recognised AND in `SUPPORTED_BACKENDS` AND passes the
codegen validation gate, but the dispatch loop in `codegen_axioms.py`
silently `continue`s on the unsupported branch. After Phase H + I, no
remaining backends are DROP'd; this row is retained as a class label for
any future backend that lands in this state before its solver runtime wires
up.

**external** — Remedies whose `:when` clause does NOT reference a
`defquery` still flow through the existing book-qa hook
(`propose_writeback.py`). The verdict surface does not gate them; they
are advisory actions read after `:unsat`. Remedies whose `:when` DOES
reference a defquery flow through the Tier 3 query-bound path (see
`wired (query-bound)` below).

**wired (query-bound)** — A `defremedy` whose `:when {:query :Q###}`
references a `defquery` name receives the query's row count bound into
its `:propose` action surface by `verdict_to_qa.py`. The remedy entry
in `verification-defects.json` carries `query_bound=true` and the
materialised row count.

**wired (alpha)** — Full end-to-end path is implemented and CI-tested
against the offline stub responder (`StubLift`). Real-provider behaviour
(OpenAI, Anthropic, local Ollama) depends on the chosen model; users
should expect proposal-quality variance and exercise the cache +
schema validation as belt-and-braces. Promoted to `wired` once
Phase Q's eval bench confirms detection rates within 5 percentage
points of the regex baseline.

**Scope modifier (REQ-CORPUS-050..056)** — A `defconstraint` may declare
`:scope :subject` (default — runs once per subject in its own solver,
matches Phase J behaviour) or `:scope :corpus` (runs once over the union
of every subject's atoms after the per-subject and shared partitions
complete). A failed `:scope :corpus` constraint surfaces on the verdict's
`:corpus-defects` field (constraint id + conflicting subjects +
explanation) rather than `:core`. See
[docs/booklogic-dsl-reference.md § 2.5 — Scope](../../docs/booklogic-dsl-reference.md#scope-req-corpus-050056)
for the worked Mizuno-trial example.

## Why this exists

Earlier iterations of the skill described `:egg` and `:cozo` as supported
backends without flagging the silent-drop behaviour. Authors wrote
constraints with those backends, observed `:sat` verdicts, and concluded
the framework had validated their claims — when in fact the constraint
had been dropped. SUPPORT_MATRIX.md + the drift lint
(`test_support_matrix.py`) keep the doc-vs-code state synchronised.

### Quantifier predicate-application semantics (v0.6)

A Keyword-headed predicate the schema declares with non-empty `:arg-sorts` and a
Bool `:return` is a Z3 **uninterpreted function**. `(:contradicts ?a ?b)` inside a
quantifier body emits `contradicts_fn.apply(&[&a_const, &b_const]).as_bool()`,
where `contradicts_fn = FuncDecl::new("contradicts", &[&sort, &sort], &Sort::bool())`
is declared once per block. The bound constants enter the predicate, so two
applications to the same arguments are the same Z3 term and the quantifier
constrains the predicate across its domain — quantified universals are now sound
(z3 refutes `(forall [?a] (:p ?a))` together with `(exists [?b] (not (:p ?b)))`).

Predicates with `nil`/empty `:arg-sorts` keep the legacy named-Bool emission
(`Bool::new_const("contradicts_a_b")`), which is sound for ground atoms; the three
shipped verifiers declare only nil-arity predicates, so their output is unchanged.

Out of scope (future): term-valued (non-Bool) uninterpreted functions; trigger
patterns (quantifiers fall back to MBQI); deep per-position argument-sort checking
beyond arity.

## Roadmap pointers

- Tier 3 (Phase H, done): `defrule` and `defconstraint :backend :egg`
  promoted from stub/DROP → wired. The codegen at
  `skills/neurosym-forge/scripts/codegen_axioms.py` now dispatches on
  `:backend`: `:z3` → `_emit_z3_block`, `:egg` → `_emit_egg_block`,
  `:cozo` → `_emit_cozo_block`. The egg backend uses `egg = "0.10"`
  (declared optional in each verifier's `Cargo.toml`, gated on the
  `eqsat` feature). Equality saturation runs under a node-count budget
  controlled by `VERIFIER_EQSAT_BUDGET` (default 10000 nodes); divergent
  rewrite sets stop at the budget rather than wedging the codegen run.
- Tier 3 (Phase I, done): `defquery`, `defconstraint :backend :cozo`,
  and query-bound `defremedy` promoted from wired-builder/DROP/external
  → wired. Cozo runs at `make ci` time via `kg::run_queries`. Cozo
  scripts are sandboxed via `VERIFIER_DATALOG_TIMEOUT_MS` (default
  10000 ms).
- Tier 2 (done in PR #77): the silent JS-to-Python regex converter is
  removed; JS-style `(?<v>)` is a hard `IngestRegexDialectError` at
  ingest time.
- Tier 3 follow-up: predicate-as-uninterpreted-function semantics for
  Keyword-headed predicates inside quantifier bodies. v0.5 wires
  `(forall [(?v :sort)] body)` / `(exists [(?v :sort)] body)` through
  `mk_forall_const` / `mk_exists_const` with typed `Datatype` bound
  constants, but Keyword-headed predicates inside the body (e.g.
  `(:contradicts ?a ?b)`) still lower to opaque Bool constants whose
  name encodes the bound-var refs. Full FOL semantics (declaring each
  predicate as `… → Bool` in the preamble and emitting `.apply(...)`
  at the call site) is deferred. See "Quantifier predicate-application
  semantics (v0.5 caveat)" above.
