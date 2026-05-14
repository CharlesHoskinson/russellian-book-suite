---
name: neurosym-forge
description: Scaffold and extend ClojureScript + Rust neurosymbolic verification projects. Use when user says "scaffold a neurosymbolic project", "verify these claims with Z3", "add a rewrite rule", "ground this predicate in Rust", "extend the atomspace IR", "build a CLJS+Rust verifier", "FOL/SMT/e-graph/Datalog verifier", or mentions MeTTa-style modeling. Composes with book-knowledge to verify ledger claims. Does NOT run verification itself — the scaffolded project does, via shadow-cljs and cargo. Do NOT use for prose review (use book-review), claim ingestion (use book-knowledge), or chapter drafting (use book-compose).
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: verification
  emits: clojurescript-rust
---

# neurosym-forge

The authoring skill for neurosymbolic verification projects in CLJS + Rust. Produces project skeletons, rewrite rules, grounded-atom modules, and IR linters. Encodes MeTTa idioms as authoring conventions.

## What it owns

- The project skeleton template for CLJS + Rust verifiers
- The EDN-as-atomspace IR specification
- The MeTTa→CLJS+Rust idiom mapping (= / : / ! / match / superpose / grounded)
- Linters for atomspace shape, sort coverage, rewrite-rule fixtures
- The scaffolder, rule-appender, grounded-atom-adder, sort-adder helpers

## What it does NOT own

- Source ingestion or claim extraction (book-knowledge)
- Running shadow-cljs or cargo builds (handled by the scaffolded project)
- Prose synthesis (book-compose)
- Editorial review (book-review)
- Defect QA (book-qa)
- Network I/O — this skill never reaches off-machine

## Components

Python helpers in `scripts/`. Invoke via `.venv\Scripts\python.exe -m scripts.<name>`.

Scaffolding:
- `scaffold_project.py` — produces the full CLJS+Rust project skeleton
- `add_rewrite_rule.py` — appends a typed `(=)` rule with fixture test
- `add_grounded_atom.py` — emits a `#[napi]` Rust function and CLJS bridge stub
- `add_sort.py` — extends the sort registry

Linting:
- `lint_atomspace.py` — every atom carries `:sort`, no unbound variables
- `lint_rewrite_coverage.py` — every rewrite rule has a fixture test
- `render_call_graph.py` — ASCII diagram of Claude↔CLJS↔Rust phase boundaries

Convenience:
- `verify_claims.py` — prints `npm run build && node ... verify` for the scaffolded project

## Composes with

- `book-knowledge` — accepts `claims/ledger.jsonl` as Phase-1 input via the `--book-knowledge-bridge` scaffold flag
- `book-qa` — optional defect class `D13: claim-set-unsatisfiable`, off by default in v0.1
- `book-thesis` — v0.2 only; not wired in v0.1

## Usage

- "Scaffold a CLJS+Rust verifier for the Bermuda claims" — full scaffold
- "Add a commutativity rule for `+`" — appends a rewrite rule
- "Ground a custom solver hook called my-fn returning :verdict" — adds a grounded atom
- "Lint the atomspace" — runs `lint_atomspace.py` on `work/atomspace.edn`

## Tests

40+ tests across the 8 modules. Run with `.venv\Scripts\python.exe -m pytest tests/ -q` from the skill root.

## See also

- `references/metta-idioms.md` — = / : / ! / match / superpose / grounded mapping
- `references/atomspace-edn.md` — the EDN IR
- `references/grounded-atoms.md` — how to wire a new Rust module
- `references/phase-boundaries.md` — what data crosses each phase boundary
- `references/rewrite-rule-style.md` — naming, doc, fixture conventions
- `references/worked-examples/osmotic-pressure/` — clojure.md example
