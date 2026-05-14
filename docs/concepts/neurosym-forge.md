# neurosym-forge — concepts

`neurosym-forge` scaffolds ClojureScript + Rust neurosymbolic verifier
projects. This document explains the design vocabulary: what the IR is,
how MeTTa idioms map onto the substrate, what the v0.3 axioms hook does,
and where the verifier plugs back into the book pipeline. The five
reference files under `skills/neurosym-forge/references/` hold the schema
detail; this page is the orientation pass.

## The problem

The book suite produces prose backed by a claim ledger. Each claim
points at its source text and links into a SHACL-validated graph.
Nothing in the
pipeline performs logical verification — no Z3 satisfiability check, no
e-graph rewrite saturation, no Datalog contradiction search beyond the
antonym pairs `book-qa` catches. The Python skills avoid native
dependencies on principle; the Rust solver bindings outclass Python's
on robustness and footprint.

Two consequences follow. First, a manuscript can pass every existing lint
gate and still contain quantitative contradictions: chapter prose
asserting eight Bermuda parishes against a canonical nine, ledger claims
that violate the van 't Hoff law, dates that contradict each other.
Second, when an author wants verification in a non-book domain — a
chemistry protocol, a legal contract, a math paper — nothing in the
suite scaffolds that work. Each new domain would require hand-rolling an
SMT pipeline from scratch.

`neurosym-forge` answers both. It emits a ClojureScript orchestrator and
a Rust verifier with an EDN-as-Atomspace intermediate representation,
wires the result into `book-qa` as an opt-in defect class, and gives the
author a small set of authoring helpers (add a sort, add a rewrite rule,
add a grounded atom) that maintain the invariants the linters enforce.
The skill itself never runs verification. The scaffolded project does
that, via `shadow-cljs` and `cargo`.

The MeTTa connection is conceptual, not literal. MeTTa is the OpenCog
Hyperon "language of thought" — a typed term-rewriting calculus with a
first-class Atomspace. `neurosym-forge` borrows its vocabulary because
the vocabulary is precise: a verifier needs atoms, sorts, equalities,
non-deterministic branches, and grounded host-language values. Treating
the EDN IR as a MeTTa-style Atomspace gives the skill a single design
language across CLJS and Rust.

## EDN-as-Atomspace IR

Every record crossing a phase boundary is an *atom*, serialised as EDN
(a JSON-compatible subset, no tagged literals beyond keywords and
sets). Atoms have one of four kinds.

A **symbol** is an identifier with a sort:

```clojure
{:kind :symbol :name :osmotic-pressure :sort {:kind :fn :args [:solution] :ret :real}}
```

A **variable** stands for a binding from a match pattern or quantifier:

```clojure
{:kind :variable :name "?s" :sort :solution}
```

A **grounded atom** is a host-language value or function pointer. The
scaffold backs each grounded atom with a `#[napi]` Rust function and a
CLJS thin shim:

```clojure
{:kind :grounded
 :name :z3-check-all
 :sort {:kind :fn :args [{:kind :vector :elem :formula}] :ret :verdict}
 :grounded {:lib :z3 :fn "check_all" :napi true}}
```

An **expression** is a list of atoms with a head and arguments:

```clojure
{:kind :expression
 :head {:kind :symbol :name := :sort :rule}
 :args [<lhs> <rhs>]
 :doc "van 't Hoff: π = iMRT"
 :id "R042"}
```

The full atomspace is a single map carrying a sort registry, a rule set,
the atom population, the grounded-atom registry, and a checksum table:

```clojure
{:version 1
 :sorts [:int :real :bool :solution :formula :verdict]
 :rules [<expression-atoms>]
 :atoms [<all other atoms>]
 :grounded [<grounded-atoms>]
 :checksums {"rules/seed.edn" "<sha256>"}}
```

`scripts/lint_atomspace.py` enforces the shape: every atom carries a
sort, every variable on a rule's `rhs` also occurs on its `lhs` (unless
the rule carries the `:eliminating` tag), every grounded atom's sort
matches its Rust signature, and the checksum on each `rules/*.edn`
matches the file content on disk. The checksum lint flags any manual edit to
`rules/*.edn`; the `add_*.py` helpers are the only sanctioned mutators.

The four-kind taxonomy is the same as MeTTa's. The top-level shape
diverges: MeTTa's Atomspace is a hypergraph indexed by content;
neurosym-forge's atomspace is a vector serialised to a single file and
loaded eagerly. `lint_atomspace.py` enforces the diverged shape. See
`references/atomspace-edn.md` for the full schema and the JSON Schema
files under `assets/schemas/`.

## MeTTa idiom mapping

The mapping is a design vocabulary, not a literal translation. Each
idiom names a recurring pattern in the scaffolded project; the
implementation lives in CLJS or Rust.

| MeTTa form | Role | Scaffolded encoding |
|---|---|---|
| `(= lhs rhs)` | function expression — `lhs` matches, `rhs` rewrites | flat rule record in `rules/*.edn`; `meander.epsilon/rewrite` in `nl_to_fol.cljs` applies the match |
| `(: x T)` | type assignment | every atom carries `:sort`; malli `m/=>` enforces at function boundaries |
| `!expr` | top-level evaluation directive | EDN metadata `^:force` on a grounded-atom shim; the CLJS phase driver evaluates immediately |
| `(match &self pattern template)` | atomspace query | `core.logic/run*` over a cozo Datalog clause, then meander template substitution |
| `(superpose (a b c))` | non-deterministic branching | CLJS `lazy-seq` of alternatives; each branch ships to Rust as a separate `assert_and_track` block |
| `(collapse expr)` | reduce a non-deterministic stream | a reduction over the lazy-seq picks one branch; the verdict EDN records the choice |
| Grounded atom | host value or function | `#[napi]` Rust function with a CLJS thin shim |
| Self-reflection | rules-as-data, programs modify their own atomspace | restricted form: `rules/*.edn` is data, but only the `add_*.py` helpers mutate it; checksums detect drift |

Two of these idioms drift from MeTTa's native semantics. The scaffold's
`^:force` analogy is not MeTTa's `!`, which is a top-level directive
only; the scaffold uses it as in-expression metadata for grounded-atom
shims. The scaffold's `collapse` selects a single verdict instead of returning
a tuple of branches; this stronger reduction reflects the scaffold's
phase-pipeline runtime, not a live REPL. `references/metta-idioms.md`
documents both divergences.

The mapping table makes one practical claim. When the author or a
downstream agent says "add an equality rule" or "ground this predicate
in Rust," the words are MeTTa's; the right `add_*.py` helper produces
the CLJS or Rust code. The skill, its helpers, its tests, and the
scaffolded project's own SKILL.md all speak the same vocabulary.

## The axioms hook (v0.3)

A verifier needs two kinds of assertion: hard domain constants that
constrain every run, and per-atom tracked assertions that participate in
the unsat core when the run fails. v0.3 separates them.

The scaffolded `rust-verifier/src/axioms.rs` ships with one function:

```rust
use z3::{Context, Solver};

pub fn assert_axioms(_ctx: &Context, _solver: &Solver) {
    // No-op default. Domain-specific verifiers replace this body.
}
```

`smt.rs::check_all` calls `crate::axioms::assert_axioms(&ctx, &solver)`
exactly once, before walking the parsed atom stream. The walk asserts
each per-atom claim under `assert_and_track` with the atom's ID as the
tracker. When Z3 returns `:unsat`, the unsat core lists the tracker IDs
that produced the contradiction; the hard axioms stay out of the core
because the walk never tracks them.

A domain-specific verifier replaces the no-op body. The Bermuda verifier
keeps its existing `canonical.rs` module (where `assert_bermuda_axioms`
encodes the six canonical facts as Z3 equalities) and ships a thin
`axioms.rs` that re-exports the canonical entry point:

```rust
pub use crate::canonical::assert_bermuda_axioms as assert_axioms;
```

A chemistry verifier (the `osmotic_pressure` example) would define
`R = 8.314` and `T = 298.15` as Z3 constants inside `assert_axioms`,
then let the per-atom walk handle the contradicting claim
(`i = 1` against the canonical `i = 2` for NaCl).

The hook is part of the v0.3 contract. Future scaffolded projects
inherit the no-op stub and override it; older Bermuda-style verifiers
keep working through the re-export shim. See
`references/grounded-atoms.md` for the full v0.3 hook documentation and
the Bermuda reference implementation.

## Composition with book-qa

`book-qa` runs Stage-1 linters over each chapter bundle, emitting defect
tickets in `qa/lint-report.json`. When a verifier exists in the
workspace, `book-qa` reads an additional file — `qa/verification-defects.json`
— and surfaces its tickets as defect class **D13: claim-set-unsatisfiable**.

The verifier writes this file. Each scaffolded project includes
`scripts/verdict_to_qa.py`, which reads the verifier's `work/verdict.edn`
and translates it. A `:sat` verdict produces an empty defects file. A
`:unsat` verdict produces one critical ticket per claim ID in the unsat
core, each pointing at the atom's source span in the ledger or chapter
prose.

The hook is opt-in per workspace, set in `examples/<workspace>/qa-config.yaml`:

```yaml
enable_verification: true
```

When the flag is off (the default), `book-qa` ignores
`verification-defects.json` entirely; the verifier still runs if invoked
directly, but its findings do not gate the build. When the flag is on,
`book-qa.lint_artifact` reads the file and a single `:unsat` verdict can
hard-fail the build via the existing `BLOCKING_DEFEASIBLE = True`
gate.

The composition is loose by design. The verifier does not call
`book-qa`; `book-qa` does not call the verifier. They share a single
artifact (`qa/verification-defects.json`) and a single config flag. The
scaffolded project owns the artifact; `book-qa` owns its consumption.
Swapping in a new Z3 version, a different solver, or a cvc5 second
opinion leaves `book-qa` untouched.

## Where to read next

- **Operator workflow.** `docs/operations/neurosym-forge-runbook.md` —
  prerequisites, scaffold, ingest, extract, add a sort/rule/grounded
  atom, wire D13, run end-to-end, troubleshoot.
- **MeTTa idioms in depth.**
  `skills/neurosym-forge/references/metta-idioms.md` — the full mapping
  table with the scope notes on `&self`, `let`, `Empty`, and
  `NotReducible`.
- **The IR schema.**
  `skills/neurosym-forge/references/atomspace-edn.md` — every field,
  every constraint, the JSON Schema files in `assets/schemas/`.
- **Grounded atoms and the axioms hook.**
  `skills/neurosym-forge/references/grounded-atoms.md` — `add_grounded_atom.py`,
  the v0.3 hook contract, the Bermuda reference implementation.
- **Phase boundaries.**
  `skills/neurosym-forge/references/phase-boundaries.md` — what data
  crosses Claude ↔ CLJS ↔ Rust at each step.
- **Rule conventions.**
  `skills/neurosym-forge/references/rewrite-rule-style.md` — rule IDs,
  doc strings, tags, fixture tests.
- **A worked end-to-end example.**
  `skills/neurosym-forge/references/worked-examples/osmotic-pressure/README.md` —
  scaffold, predicates, the van 't Hoff rule, a grounded atom for the
  gas constant, both the clean (`:sat`) and the doctored (`:unsat`) run.
- **The skill spec.** `skills/neurosym-forge/SKILL.md` — public entry
  point with trigger phrases, ownership boundaries, and the full helper
  inventory.
