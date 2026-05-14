# neurosym-forge — Design

Date: 2026-05-13
Author: Charles (with Claude)
Status: Draft, pending user approval

## Problem

The book suite produces prose backed by a claim ledger. Every claim today is supported by source text and a SHACL-validated graph, but nothing in the pipeline performs *logical* verification — Z3-style satisfiability, e-graph algebraic equivalence, Datalog cross-claim contradiction beyond simple antonym pairs. Adding that capability inside the existing Python skills would mean grafting a solver stack onto a pipeline whose discipline is "no paid APIs, no network, no heavy native dependencies" — and Python's solver bindings (z3-solver, py-z3) are heavier and more fragile than the Rust equivalents.

A second problem: when the user wants to verify claims in *another* domain — a math paper, a legal contract, a chemistry protocol — there is no skill that scaffolds a verification project for that domain. Each new domain would otherwise require hand-rolling an SMT pipeline.

A third problem, on the language side: ClojureScript + Rust is the right substrate for symbolic verification (CLJS for term rewriting, Rust for the SMT/e-graph/Datalog runtime), and no existing skill helps an agent write that style of code. The `neurosym-verify` writeup in `clojure.md` (May 2026) gives a complete blueprint for one such project but is not itself a skill; it is a one-off design.

## What v0.1 ships

A new sibling skill `neurosym-forge` at `skills/neurosym-forge/` that **scaffolds and extends neurosymbolic verification projects in ClojureScript + Rust**. The skill produces project skeletons, appends new rewrite rules, adds grounded-atom Rust modules, and lints the intermediate representation. It does **not** itself run verification — the scaffolded project does that via `shadow-cljs` and `cargo`.

The skill encodes idioms from MeTTa (the OpenCog Hyperon "language of thought") as authoring conventions. Treating the EDN intermediate representation as a MeTTa-style Atomspace gives the skill a coherent vocabulary for talking about atoms, types, equalities, evaluation, and grounded values across the two host languages.

### Architecture (skill level)

```
       book-knowledge ──claim ledger──┐
                                      │  optional input
                                      ▼
                         ┌────────────────────────────┐
                         │ neurosym-forge (this skill) │
                         │                              │
                         │  scaffold_project ─► CLJS+   │
                         │                      Rust    │
                         │                      project │
                         │                              │
                         │  add_rewrite_rule            │
                         │  add_grounded_atom           │
                         │  add_sort                    │
                         │  lint_atomspace              │
                         │  lint_rewrite_coverage       │
                         │  render_call_graph           │
                         └──────────────┬───────────────┘
                                        │ produces
                                        ▼
                         ┌────────────────────────────┐
                         │  scaffolded project          │
                         │  (e.g. examples/             │
                         │       osmotic-pressure/)     │
                         │                              │
                         │  ├── cljs-orchestrator/      │
                         │  ├── rust-verifier/          │
                         │  ├── templates/              │
                         │  └── SKILL.md                │
                         └──────────────┬───────────────┘
                                        │ scaffolded project
                                        │ exports `verify_claims.cli`
                                        ▼
                                  optional D13 (claim-set
                                  unsatisfiable) added to
                                  book-qa Stage-1 linter
```

### Architecture (scaffolded project level)

The scaffolded project follows the pipeline from `clojure.md` verbatim, with one difference: the EDN intermediate representation is documented and enforced as a MeTTa-style Atomspace.

```
  source documents (PDFs, .md, .txt)         claim ledger (JSONL, optional)
            │                                       │
            └───────────┬───────────────────────────┘
                        ▼
            ┌──────────────────────┐
            │ Phase 1: Extraction  │  Claude reads sources, emits atoms
            │ (Claude)             │  into work/atomspace.edn
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Phase 2: Rewrite     │  CLJS orchestrator applies (=) rules,
            │ (cljs-orchestrator)  │  malli enforces (:) sort declarations,
            │                      │  superpose generates non-det branches
            └──────────┬───────────┘
                       │ napi-rs FFI
                       ▼
            ┌──────────────────────┐
            │ Phase 3: Verify      │  Grounded atoms execute:
            │ (rust-verifier)      │  z3 (SMT), egg (e-graph),
            │                      │  cozo (Datalog contradiction)
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Phase 4: Synthesis   │  Claude reads only verified atoms,
            │ (Claude)             │  writes report.md
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Phase 5: Typeset     │  tectonic in-process LaTeX→PDF
            │ (rust-verifier)      │
            └──────────────────────┘
```

## MeTTa idioms mapped to CLJS + Rust

The skill's central conceptual contribution is the mapping table below, encoded in `references/metta-idioms.md` and enforced by linters in `scripts/`.

| MeTTa form | Semantics | Encoding in scaffolded CLJS + Rust |
|---|---|---|
| `(= lhs rhs)` | Equality declaration; defines `lhs` as rewritable to `rhs` | `meander.epsilon/rewrite` clause pair in `nl_to_fol.cljs`; the equality is stored as an EDN record `{:= [lhs rhs] :doc "..." :id ...}` so the skill can introspect and version rule sets |
| `(: x T)` | Type declaration: atom `x` has sort `T` | Every atom in EDN carries `:sort` (one of `:int`, `:real`, `:bool`, `:entity`, `(:fn [args] ret)`, `(:enum kw+)`); malli `m/=>` schemas enforce sorts at function boundaries |
| `!expr` | Force-evaluate `expr` now (do not store as data) | EDN metadata `^:force` on an atom; the CLJS phase driver evaluates immediately and replaces the atom in-place with the result |
| `(match $space pattern template)` | Query the atomspace and project results through a template | core.logic `run*` over a cozo Datalog query (the atomspace is the cozo store), then meander template substitution |
| `(superpose (a b c))` | Non-deterministic choice: produce three branches | CLJS `lazy-seq` of alternatives; each branch is sent to Rust as a separate `assert_and_track` block with a distinct branch tracker |
| `(collapse expr)` | Reduce a non-deterministic stream to one value | Reduction over the lazy-seq in `phases.cljs`; the verdict EDN reports which branch was chosen and why |
| Grounded atom | A host-language value (number, string, opaque pointer) that participates in matching but executes natively | A `#[napi]` Rust function wrapped in a CLJS thin shim. The atom carries `:grounded {:lib :z3 :fn "check_all" :args [...]}`. The scaffolder generates the napi-rs binding stub automatically |
| Self-reflection (programs read/modify their own code) | The rule set itself is data — rules can match other rules | All `(=)` rules live in EDN files (`rules/*.edn`) loaded at startup. The skill's `add_rewrite_rule.py` is the only sanctioned editor; it appends to the EDN, validates the rule against the sort registry, and writes a fixture test |
| Atomspace | The hypergraph of all atoms | The cozo `claim` table plus the in-memory `core.logic.pldb` database, snapshotted to `work/atomspace.edn` on each phase boundary |

This mapping is not a one-to-one translation of MeTTa to CLJS+Rust — it is a *design vocabulary*. When the skill (or a user) talks about "adding an equality rule" or "grounding this predicate in Rust," the words are MeTTa's; the implementation is CLJS+Rust.

## Skill layout

```
skills/neurosym-forge/
├── SKILL.md                              entry point; description, triggers, usage
├── LICENSE                               MIT (matches the rest of the suite)
├── pyproject.toml                        Python 3.13, scripts are Python
├── scripts/
│   ├── __init__.py
│   ├── scaffold_project.py               emits the full CLJS+Rust skeleton
│   ├── add_rewrite_rule.py               appends a (=) rule, validates sorts
│   ├── add_grounded_atom.py              emits a #[napi] fn + CLJS bridge stub
│   ├── add_sort.py                       extends the type registry
│   ├── lint_atomspace.py                 every atom has :sort; no unbound vars
│   ├── lint_rewrite_coverage.py          every rule has a fixture test
│   ├── render_call_graph.py              ASCII diagram of phase boundaries
│   └── verify_claims.py                  convenience wrapper: build + run
├── references/                           progressive disclosure
│   ├── metta-idioms.md                   the mapping table above, with examples
│   ├── atomspace-edn.md                  the EDN-as-atomspace IR
│   ├── grounded-atoms.md                 how to add a new Rust verifier module
│   ├── phase-boundaries.md               what crosses Claude↔CLJS↔Rust
│   ├── rewrite-rule-style.md             naming, doc, fixture conventions
│   └── worked-examples/
│       ├── osmotic-pressure/             the clojure.md example, regenerated
│       └── claim-ledger-bridge/          verify book-knowledge claims
├── assets/
│   ├── project-template/                 the scaffolded skeleton
│   │   ├── shadow-cljs.edn.tmpl
│   │   ├── package.json.tmpl
│   │   ├── deps.edn.tmpl
│   │   ├── Cargo.toml.tmpl
│   │   ├── build.rs.tmpl
│   │   ├── cljs-orchestrator/
│   │   │   └── src/main/{{project}}/
│   │   │       ├── core.cljs.tmpl
│   │   │       ├── phases.cljs.tmpl
│   │   │       ├── ir.cljs.tmpl
│   │   │       ├── nl_to_fol.cljs.tmpl
│   │   │       ├── unify.cljs.tmpl
│   │   │       └── bridge.cljs.tmpl
│   │   ├── rust-verifier/
│   │   │   └── src/
│   │   │       ├── lib.rs.tmpl
│   │   │       ├── smt.rs.tmpl
│   │   │       ├── eqsat.rs.tmpl
│   │   │       ├── kg.rs.tmpl
│   │   │       ├── ir.rs.tmpl
│   │   │       └── typeset.rs.tmpl
│   │   ├── templates/
│   │   │   ├── report.tex.tera.tmpl
│   │   │   └── claim_table.tex.tera.tmpl
│   │   ├── rules/
│   │   │   └── seed.edn.tmpl
│   │   └── SKILL.md.tmpl                 each scaffolded project is itself a skill
│   └── schemas/
│       ├── atom.schema.json              JSON Schema for atom records
│       ├── rewrite-rule.schema.json      JSON Schema for (=) rules
│       └── sort.schema.json              JSON Schema for the sort registry
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── fixtures/
    │   ├── valid_atom.edn
    │   ├── invalid_atom_missing_sort.edn
    │   └── ...
    ├── test_scaffold_project.py
    ├── test_add_rewrite_rule.py
    ├── test_add_grounded_atom.py
    ├── test_add_sort.py
    ├── test_lint_atomspace.py
    ├── test_lint_rewrite_coverage.py
    ├── test_render_call_graph.py
    ├── test_anthropic_compliance.py
    ├── test_trigger_calibration.py
    ├── trigger_tests.yaml
    └── smoke-results.md
```

The scaffolded project (under `examples/<project>/` or wherever the user scaffolds) is itself self-describing: it contains a `SKILL.md` so the resulting verifier can be installed and invoked by Claude Code as a sibling skill. This is the self-reflection idiom — the scaffolder is a skill that scaffolds skills.

## Draft SKILL.md

```markdown
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
- `verify_claims.py` — wraps `npm run build && node ... verify` for the scaffolded project

## Composes with

- `book-knowledge` — accepts `claims/ledger.jsonl` as Phase-1 input; emits `verdict.edn` whose contradictions feed back as proposed transitions
- `book-qa` — optional defect class `D13: claim-set-unsatisfiable`, off by default in v0.1 and enabled per-workspace via `qa-config.yaml`
- `book-thesis` — v0.2 only; not wired in v0.1

## Usage

- `/neurosym-forge scaffold osmotic-pressure` — emit a new project at `examples/osmotic-pressure/`
- `/neurosym-forge add-rule "(= (osmotic-pressure ?s) (* i M R T))"` — append a rewrite rule to the current project
- `/neurosym-forge add-grounded z3-check :lib z3 :sort :verdict` — add a grounded atom backed by a Rust function
- `/neurosym-forge lint` — run all linters
- "Scaffold a CLJS+Rust verifier for the Bermuda claims" — full scaffold scoped to the current workspace

## Tests

~40 tests across 7 files. Run with `pytest` from the skill root.

## See also

- `references/metta-idioms.md` — = / : / ! / match / superpose / grounded mapping
- `references/atomspace-edn.md` — the EDN IR
- `references/grounded-atoms.md` — how to wire a new Rust module
- `references/phase-boundaries.md` — what data crosses each phase boundary
- `references/worked-examples/osmotic-pressure/` — the clojure.md example regenerated
```

## EDN-as-Atomspace IR

The intermediate representation across all phase boundaries is EDN. Every record is an *atom*. Atoms have one of four kinds, matching MeTTa's atom taxonomy.

```clojure
;; Symbol atom — an identifier, the most common kind
{:kind :symbol
 :name :osmotic-pressure
 :sort (:fn [:solution] :real)}

;; Variable atom — bound by a quantifier or a match pattern
{:kind :variable
 :name "?s"
 :sort :solution}

;; Grounded atom — a host-language value or function pointer
{:kind :grounded
 :name :z3-check-all
 :sort (:fn [(:vector :formula)] :verdict)
 :grounded {:lib :z3 :fn "check_all" :napi true}}

;; Expression atom — a parenthesised list of atoms
{:kind :expression
 :head {:kind :symbol :name := :sort :rule}
 :args [{:kind :expression :head ... :args [...]}
        {:kind :expression :head ... :args [...]}]
 :doc "van 't Hoff: π = iMRT"
 :id "R042"}
```

The full atomspace is a vector of atoms, plus a top-level sort registry and rule registry:

```clojure
{:sorts   [:int :real :bool :solution :formula :verdict ...]
 :rules   [<rule-atoms>]
 :atoms   [<all other atoms>]
 :version 1}
```

This shape is enforced by `lint_atomspace.py` and the JSON Schemas in `assets/schemas/`.

## Rewrite rule shape

A rewrite rule is an expression atom whose head is `:=`:

```clojure
{:kind :expression
 :head {:kind :symbol :name := :sort :rule}
 :args [<lhs-atom> <rhs-atom>]
 :doc  "comment for humans"
 :id   "R001"
 :tags #{:algebraic :commutative}}
```

`add_rewrite_rule.py` appends to `rules/<file>.edn`, validates that every variable in `lhs` appears in `rhs` (and vice versa unless tagged `:eliminating`), checks sorts via the registry, and emits a fixture test in `tests/rules/test_R001.cljs` of the scaffolded project.

## Grounded-atom protocol

Adding a new grounded atom is the most error-prone operation in the scaffolded project. `add_grounded_atom.py` automates it:

1. Reads the requested name, sort, library tag, and Rust function signature.
2. Appends a `#[napi]` function stub to `rust-verifier/src/<lib>.rs`, wired into `lib.rs` as a public entry point. The body is `todo!()` with a comment block listing the contract.
3. Appends a CLJS bridge stub to `cljs-orchestrator/src/main/<project>/bridge.cljs`.
4. Appends a grounded-atom record to `rules/grounded.edn`.
5. Adds a fixture test in `tests/grounded/` of the scaffolded project (a contract test that calls the napi-rs function with a stub input and asserts the result shape).
6. Prints a TODO with the file paths the user must edit to fill in the `todo!()` body.

This is the seam where the skill stops generating and the user starts writing solver-specific logic.

## Self-reflection

The skill is self-reflective in the MeTTa sense: the rule set itself is data, editable by the same skill that emits projects. Three consequences:

1. `add_rewrite_rule.py` reads the current `rules/*.edn`, deduplicates, sorts by tag, and writes the result back. It is the *only* sanctioned editor; manual edits are detected via a file-level checksum stored in `rules/.checksums.edn` and flagged by `lint_rewrite_coverage.py`.
2. The scaffolded project's own `SKILL.md.tmpl` exposes `add-rule` and `add-grounded` so a downstream user (or Claude) can extend the project after scaffold without re-running `neurosym-forge`.
3. The skill itself is versioned. `scaffold_project.py` writes the `neurosym-forge` version into `rules/.forge-version.edn` so the scaffolded project can detect when the skill has drifted from its scaffold and the linter can re-validate against the new sort registry.

## Composition with existing skills

### book-knowledge bridge

A scaffolded project can consume `claims/ledger.jsonl`. The bridge is a Python helper in `scripts/ingest_ledger.py` (inside the scaffolded project, not the skill) that:

- Reads claims via `book-knowledge.scripts.io_utils.read_jsonl`
- Filters to `:tbf:status :verified` claims
- Emits `work/atomspace.edn` with one expression atom per claim, sort-annotated from the claim's `:p` predicate via a project-local predicate-to-sort map

`neurosym-forge.scripts.scaffold_project` accepts a `--book-knowledge-bridge` flag that emits this helper and adds the project-local predicate map to `rules/predicates.edn`.

### book-qa D13

A new defect class is added to `book-qa` when a scaffolded verifier exists in the workspace:

- **D13** claim-set-unsatisfiable — Z3 returned `:unsat` on the verified-claim set; the unsat core lists the offending claim IDs

The check is run by `book-qa.scripts.lint_artifact` only if `examples/<verifier>/dist/main.js` exists for the workspace. Adding this to book-qa is a one-line change in `lint_artifact.py` plus a new ticket type in `qa/schema.json`. It is optional and gated by configuration.

### book-thesis integration

`book-thesis`'s entailment loop currently uses Datalog-only reasoning. With a scaffolded verifier present, entailment can call into the verifier's `verify_formulas` napi function via a thin subprocess shim. This is **deferred to v0.2** — out of scope for the v0.1 design.

## Anthropic skill compliance

The skill follows the same Anthropic best practices as the other skills in the suite:

- SKILL.md frontmatter description fits within 1024 characters and uses concrete trigger phrases
- Body of SKILL.md is well under 500 lines
- Progressive disclosure: reference docs in `references/`, asset templates in `assets/`, never inlined into SKILL.md
- All scripts emit machine-readable output (JSON or EDN) for orchestration; human-readable summaries are secondary
- No network I/O
- No paid APIs
- pytest fixtures stub all LLM calls

## What this skill does NOT ship in v0.1

- A working Z3 / egg / cozo runtime — that lives inside the scaffolded project, not the skill. The skill emits stubs that compile but require `cargo build` to produce a native addon.
- WASM target for the scaffolded Rust addon — the skill emits cdylib only. WASM is a v0.3 target.
- A second SMT solver (cvc5) — the skill emits Z3-only stubs. cvc5 second-opinion mode is a v0.2 target.
- Lean / Coq proof export — out of scope.
- A `book-thesis` integration — deferred to v0.2.
- An automatic re-run loop when the verifier returns `:unsat` — the skill emits the scaffolding for it, but the loop is in the scaffolded project, not the skill. The skill itself is stateless.

## Open questions

1. **Where do scaffolded projects live?** Default: `examples/<project>/` inside the user's current workspace. Alternative: a sibling `verifiers/` directory at workspace root. Recommendation: `verifiers/<project>/` to keep books and verifiers cleanly separated; revisit after the first real use.
2. **Does the skill ship a vendored Z3 source tree?** No — the scaffolded project's `Cargo.toml` declares `z3 = { version = "0.20", features = ["bundled"] }`, which vendors Z3 at build time. The skill itself ships no binary blobs.
3. **Does `add_rewrite_rule.py` accept MeTTa syntax directly, or only EDN?** v0.1: EDN only. v0.2: a thin MeTTa parser (`metta-rs` or hand-rolled nom) that converts `(= (f $x) (g $x))` strings to the EDN rule record.
4. **Trigger calibration:** how aggressive should the skill be on phrases like "verify these claims"? Recommendation: medium aggressiveness — fire on explicit mentions of FOL/SMT/Z3/e-graph/Datalog/MeTTa, but defer to book-qa for the generic "check this manuscript" intent.

## Estimated effort

- Scaffolder + templates + idiom mapping: 1.5 days
- Linters and add-rule/add-grounded helpers: 1 day
- Worked example (osmotic-pressure regenerated end-to-end): 0.5 day
- Tests (40-ish): 1 day
- Documentation pass (references/): 0.5 day

Total: **4-5 days** for one engineer familiar with CLJS, Rust, and the existing skill suite. The long pole is the worked example, since it requires actually building the CLJS+Rust project the scaffold emits and confirming it runs end-to-end on a representative input.
