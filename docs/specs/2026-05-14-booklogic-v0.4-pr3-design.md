# BookLogic v0.4 PR-3 — Design

Date: 2026-05-14
Author: Charles
Status: Draft, pending user approval
Parent spec: `docs/specs/2026-05-14-booklogic-v0.4-mission-design.md`
Revision: 2026-05-14 — directional decision: pure CLJS + Rust for the verifier path; no new Python BookLogic semantics.

## Problem

After PR-1 and PR-2 of v0.4 shipped, two pieces of the umbrella mission remain unaddressed:

1. **Predicate definitions live in three files.** Bermuda's `rules/predicates.edn` carries the regex catalog; `verifiers/bermuda/scripts/ingest_ledger.py` carries the predicate-to-value coercion; `rust-verifier/src/canonical.rs` carries the Z3 axiom. Adding a predicate requires editing three files in lockstep with no schema enforcing they agree.
2. **No BookLogic compiler exists.** The DSL is defined in the umbrella spec but no code consumes its forms. The first three declaration forms (`defsort`, `defpredicate`, `deflift`) are the foundation; without them, the active forms in PR-4 have nothing to attach to.

A third, architectural, decision: PR-3 commits the verifier path to pure CLJS + Rust. Python remains only where it already lives (`book-knowledge` upstream; the scaffolder's templating; `book-qa` downstream). The BookLogic compiler is CLJS. The existing Python ingesters in `verifiers/bermuda/scripts/` keep running unchanged — they consume the `predicates.edn` the new CLJS compiler emits.

## Mission

Ship BookLogic core: `defsort`, `defpredicate`, `deflift` — as a pure CLJS compiler. End-to-end correctness verified by a live nbb integration test. No Python BookLogic semantics anywhere.

Five concrete deliverables:

- **D1.** `cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl` — the BookLogic compiler. Reads `rules/booklogic/{sorts,predicates,lifts}.edn`; produces (a) in-memory atomspace IR consumable by `phases.cljs` and (b) on-disk `rules/predicates.edn` for the existing Python ingester.
- **D2.** Scaffolder integration — emit empty `rules/booklogic/` directory + `package.json` with `nbb` devDependency + `npm run booklogic-compile` script in new projects.
- **D3.** Live nbb integration test — Python test harness that scaffolds a temp project, runs `npm install`, invokes `npm run booklogic-compile`, asserts the compiler produces correct atomspace IR AND a fired lift rule.
- **D4.** Template-shape tests — fast-feedback grep-style checks on the `.cljs.tmpl` file.
- **D5.** New CI job for Node-toolchain-dependent tests.

## Architecture

```
   rules/booklogic/                         BookLogic source (opt-in)
   ├── sorts.edn                            (defsort ...)
   ├── predicates.edn                       (defpredicate ...)
   └── lifts.edn                            (deflift ...)
            │
            │ single reader
            ▼
   ┌────────────────────────────────────────────────┐
   │     CLJS BookLogic compiler (booklogic.cljs)   │
   ├────────────────────────────────────────────────┤
   │                                                 │
   │   - reads booklogic/*.edn                       │
   │   - expands defsort     → sort registry entries │
   │   - expands defpredicate → predicate registry   │
   │   - expands deflift     → meander rewrite rules │
   │   - emits atomspace IR (in memory)              │
   │   - codegens rules/predicates.edn (for Python   │
   │     ingester for D1-D3 forms)                   │
   │                                                 │
   └─────────┬──────────────────────┬───────────────┘
             │                      │
             ▼                      ▼
    in-memory IR             rules/predicates.edn
    consumed by              consumed by Python
    phases.cljs              ingest_ledger.py (legacy)
```

The detection rule: if `rules/booklogic/` exists in a project, it is the authoritative BookLogic source and the compiler regenerates `predicates.edn`. If the directory is absent, `predicates.edn` is hand-maintained (Bermuda's current world; preserved untouched until PR-5).

## D1 — CLJS BookLogic compiler

New template file `skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl` (~280 lines).

### Public API

```clojure
(ns {{ project_slug }}.booklogic
  "BookLogic v0.4 declaration-form compiler — reads rules/booklogic/*.edn,
   produces atomspace IR + codegens rules/predicates.edn."
  (:require [cljs.reader :as edn]
            [meander.epsilon :as m]
            [clojure.string :as str]
            ["fs" :as fs]
            ["path" :as path]))

(defn load-booklogic
  "Read all three BookLogic source files from project-root/rules/booklogic/.
   Returns a map: {:sorts [...] :predicates [...] :lifts [...]}."
  [project-root])

(defn expand
  "Expand the loaded BookLogic source into atomspace IR.
   Returns: {:sort-registry [...] :predicate-registry [...] :lift-rules [...]}."
  [booklogic-source])

(defn emit-predicates-edn
  "Codegen the predicates.edn artifact for the legacy Python ingester.
   Generated for compatibility with the existing Python ingest_ledger.py."
  [expanded out-path])

(defn -main
  "CLI entry — read booklogic/*.edn, expand, write predicates.edn.
   Invoked as: nbb -m {{ project_slug }}.booklogic <project-root>"
  [& args])
```

### Recognised forms

The compiler dispatches on the head symbol of each top-level list:

#### `defsort`

```clojure
(defsort :entity)
(defsort :int)
(defsort :real)
(defsort :bool)
(defsort :solution)
(defsort {:kind :fn :args [:solution] :ret :real})
(defsort {:kind :enum :members [:sat :unsat :unknown]})
```

Compiles to entries in the in-memory sort registry. Primitive sorts (keywords) and structured sorts (fn, enum) both supported.

Validation: each sort must be either a `Keyword` or a map with `:kind :fn` + `:args` + `:ret`, or `:kind :enum` + `:members`. No duplicates within `sorts.edn`.

#### `defpredicate`

```clojure
(defpredicate :parishes-count [:entity] :int)
(defpredicate :currency-pegged-at-parity [:entity] :bool)
(defpredicate :airport-on-island [:entity] :entity)
```

Syntax: `(defpredicate <name-kw> <arg-sorts-vec> <return-sort>)`.

Validation: name must be a `Keyword`; every sort referenced must be declared in `sorts.edn` (or be a primitive); no duplicates within `predicates.edn`.

Compiled to the in-memory predicate registry. Also contributes to the `predicates.edn` codegen output (with empty regex patterns by default; the `deflift` form fills patterns in).

#### `deflift`

```clojure
(deflift L001-parish-count
  :from :claim/canonical-text
  :when "(?i)(?<n>\\d+|nine|eight|seven)\\s+(traditional\\s+)?parishes?"
  :emit (fact ?claim-id :Bermuda :parishes-count (parse-int ?n))
  :word-to-int {"nine" 9 "eight" 8 "seven" 7}
  :provenance :inherit
  :confidence :inherit)
```

Syntax: `(deflift <name-sym> <option-map-as-key-value-pairs>)`.

Required options:
- `:from` — slot of the source claim to scan (e.g., `:claim/canonical-text`)
- `:when` — regex as a string (PR-3 does not add EDN regex-literal `#"..."` reader support; that lands in v0.5)
- `:emit` — the target atom form; a fact-style S-expression with bound variables

Optional options:
- `:word-to-int` — map English number words to ints
- `:provenance` — `:inherit` (default) or an explicit atom
- `:confidence` — `:inherit` (default) or a literal double

Compilation:
- **CLJS in-memory:** a meander rewrite clause that matches `:from`'s value against `:when`'s regex, then constructs `:emit`'s atom with named-capture variables bound from the regex (and `:word-to-int` applied if present)
- **predicates.edn codegen:** an entry in the legacy Python-consumable format:

```clojure
{:patterns ["(?i)(?<n>\\d+|nine|eight|seven)\\s+(traditional\\s+)?parishes?"]
 :predicate :parishes-count
 :subject :Bermuda
 :value-kind :int
 :word-to-int {"nine" 9 "eight" 8 "seven" 7}}
```

This is the SAME shape Bermuda has today; the codegen path keeps the existing Python ingester working unchanged.

### Error model

The compiler throws `(ex-info ...)` on:
- Unknown form head (anything other than `defsort`/`defpredicate`/`deflift`)
- Predicate referencing an undeclared sort
- Lift referencing an undeclared predicate
- Duplicate definitions within or across the three files
- Missing required option on `deflift`

The CLI exits with non-zero on compiler errors; exits 0 with a stdout report on success.

## D2 — Scaffolder integration

`skills/neurosym-forge/scripts/scaffold_project.py` gains:

1. Emit `rules/booklogic/` with three minimal seed files:
   - `sorts.edn` → `{:forms []}`
   - `predicates.edn` → `{:forms []}`
   - `lifts.edn` → `{:forms []}`

2. Emit/merge `package.json` to include:
   ```json
   {
     "devDependencies": {
       "nbb": "^1.2.0"
     },
     "scripts": {
       "booklogic-compile": "nbb -m {{ project_slug }}.booklogic ."
     }
   }
   ```

   If a `package.json` already exists (e.g., the v0.3 template emits one), MERGE rather than overwrite — preserve existing `scripts` and `devDependencies`.

3. Emit a `cljs-orchestrator/src/test/__project__/booklogic_test.cljs.tmpl` — a small CLJS test fixture that the live integration harness can run.

Bermuda has no `rules/booklogic/` directory; its scaffolder run predates this change; no behaviour change for it. PR-5 will add `rules/booklogic/` to Bermuda as part of its full BookLogic migration.

## D3 — Live nbb integration test (the C-flavour deliverable)

New file: `skills/neurosym-forge/tests/test_cljs_integration.py`.

### What it does

A single end-to-end scenario in one Python test:

1. Use `scaffold_project` to emit a temp project at `tmp_path/test_project/`.
2. Write three fixture BookLogic source files into `rules/booklogic/`:
   - `sorts.edn`: `{:forms [(defsort :entity) (defsort :int)]}`
   - `predicates.edn`: `{:forms [(defpredicate :parishes-count [:entity] :int)]}`
   - `lifts.edn`: `{:forms [(deflift L001 :from :claim/canonical-text :when "(?i)(?<n>\\d+) parishes?" :emit (fact ?claim-id :Bermuda :parishes-count (parse-int ?n)))]}`
3. Run `npm install` in the scaffolded project (downloads nbb).
4. Run `npm run booklogic-compile` which invokes nbb against the rendered `booklogic.cljs`.
5. The compiler reads the three fixture files, emits `rules/predicates.edn` in the legacy format.
6. The Python test asserts:
   - `predicates.edn` exists and parses as real EDN
   - Contains one predicate entry keyed `:parishes-count`
   - The entry's `:patterns` vector contains the regex from the lift
   - The entry's `:value-kind` is `:int`

Also runs the test fixture:

7. Run `npm test` which invokes nbb against `booklogic_test.cljs`. The test fixture:
   - Calls `(booklogic/load-booklogic ".")` and asserts the loaded source matches
   - Calls `(booklogic/expand ...)` and asserts the atomspace IR has 2 sorts, 1 predicate, 1 lift rule
   - Constructs a fixture claim `{:claim/id "C001" :claim/canonical-text "Bermuda has 9 parishes."}` and asserts the lift rule fires, producing `{:kind :expression :predicate :parishes-count :subject :Bermuda :value 9 :id "C001"}`
8. nbb exits 0 on success, non-zero on failure; the Python harness asserts both exit codes.

### Why this is the C-flavour

The test runs actual CLJS code against actual fixtures and asserts actual compiler output. It catches:
- BookLogic form parsing bugs
- Sort/predicate registry bugs
- Lift expansion bugs in the meander rewrite
- predicates.edn codegen shape bugs
- The lift rule's actual runtime behaviour against a claim

No template-shape grep substitutes for this; the integration test is the single source of correctness for the CLJS compiler.

### CI dependencies

Node 22+ via `actions/setup-node@v4`; `npm install` step caches `node_modules/`. Test runs only `test_cljs_integration.py` (the rest of the suite stays in the existing CI). This isolates the Node dependency to one targeted job.

## D4 — Template-shape tests

`skills/neurosym-forge/tests/test_template_shape.py` (rename from `test_rust_template_shape.py` to reflect broader scope) gains:

- `test_booklogic_template_exists` — `booklogic.cljs.tmpl` is at the expected path
- `test_booklogic_template_has_main` — contains a `-main` function (CLI entry)
- `test_booklogic_template_has_three_form_dispatchers` — contains the strings `defsort`, `defpredicate`, `deflift`
- `test_booklogic_template_emits_predicates_edn` — contains `emit-predicates-edn` reference and a `fs/writeFileSync` call

These run fast (no Node), catch template drift before the heavy nbb test. They complement the live integration test rather than replacing it.

## D5 — CI job

`.github/workflows/booklogic-cljs-test.yml`:

```yaml
name: BookLogic CLJS integration

on:
  pull_request:
  push:
    branches: [main]

jobs:
  cljs-integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: npm
      - run: cd skills/neurosym-forge && python -m venv .venv && .venv/bin/pip install -e ".[dev]"
      - run: cd skills/neurosym-forge && .venv/bin/python -m pytest tests/test_cljs_integration.py -v
```

The job runs only the live integration test. The other 146 neurosym-forge tests stay in the existing CI flow (Python-only, no Node dependency).

## Test surface

| Surface | Test file | Count | What it covers |
|---|---|---|---|
| Scaffolder integration | `tests/test_scaffold_project.py` (existing) | +2 | new project has empty `rules/booklogic/`; new project has `package.json` with nbb |
| Template shape | `tests/test_template_shape.py` (renamed) | +4 | `booklogic.cljs.tmpl` shape checks |
| **CLJS live integration** | `tests/test_cljs_integration.py` (NEW) | 1 (heavyweight) | end-to-end: scaffold → npm install → nbb compile → assert predicates.edn + atomspace IR + lift fires |
| **Total new tests** | | **7** | |

This is fewer tests than the previous draft (24 → 7) because the heavy lifting moves into the live integration test, which exercises far more behaviour per test than unit tests can.

## Non-goals

- **The four active forms** (`defrule`, `defconstraint`, `defquery`, `defremedy`) — PR-4
- **Bermuda migration to BookLogic** — PR-5
- **osmotic-pressure verifier built on BookLogic** — PR-6
- **Regex literal (`#"..."`) support in the EDN reader** — v0.5; regex is a string in v0.4
- **defentity, defgate, defbackend, defmetric** — out of scope per umbrella spec
- **SCI sandbox** — "no eval" stance preserved; CLJS runs in vanilla nbb, no dynamic code

## Workspace mutation policy

PR-3 touches:

- `skills/neurosym-forge/assets/project-template/` (new `booklogic.cljs.tmpl`, new `booklogic_test.cljs.tmpl`, `rules/booklogic/` stub files, `package.json.tmpl` updates)
- `skills/neurosym-forge/scripts/scaffold_project.py` (emit new template files; merge package.json)
- `skills/neurosym-forge/tests/` (rename + extend template-shape test; new live integration test)
- `.github/workflows/booklogic-cljs-test.yml` (new CI job)

PR-3 does NOT touch:

- `verifiers/bermuda/scripts/*.py` (preserved)
- `verifiers/bermuda/rules/predicates.edn` (preserved; Bermuda has no `rules/booklogic/` so the new compiler is inert for it)
- `examples/bermuda-manual/` (read-only as always)
- `skills/book-knowledge/` (no changes; the trace exporter shipped in PR-2)
- `skills/book-qa/` (no changes)
- Any sibling skill's source code

## Revised v0.4 mission slate

PR-3.5 was floated as a "port Python ingesters to CLJS" follow-up but is not part of the v0.4 mission slate; PR-cleanup (see docs/specs/2026-05-17-booklogic-claude-only-finish-design.md) closes the remaining D1 hygiene gap instead. The mission slate is the six-PR set in the v0.4 mission spec. The "pure CLJS + Rust verifier path" remains an aspirational end state but is not gated by this PR.

## Risks

1. **Node toolchain in CI (new dependency).** The existing CI doesn't use Node; PR-3 introduces it via a separate job. Mitigation: the new job is isolated from the existing Python CI; if Node fails, only the live integration test fails, not the full suite.
2. **Cross-platform EDN regex semantics.** Node's regex engine (V8) differs from Python's `re` module on some edge cases (lookbehind, character classes). Mitigation: the BookLogic regex strings are written once in `lifts.edn` and consumed by both the CLJS compiler (Node regex) and the legacy Python ingester (Python regex). For PR-3, only the CLJS side runs the regex during compilation (it just stores the string for codegen); Python still applies it at ingest. The regex must work in BOTH engines. The integration test exercises only the CLJS pathway.
3. **nbb startup latency (~3-5s).** The integration test runs once per PR; acceptable.
4. **Template-rendering for tests.** The `.tmpl` files use jinja `{{ project_slug }}`. The integration test renders them via the scaffolder before nbb runs. Straightforward.
5. **Accidental Bermuda regeneration.** Bermuda has no `rules/booklogic/`; the compiler is silent. A smoke test asserts Bermuda's `predicates.edn` byte-stability across the PR.

## Estimated effort

~2.5 days.

- Day 1: `booklogic.cljs.tmpl` (parser + sort registry + predicate registry + lift expansion)
- Day 2: `booklogic.cljs.tmpl` (predicates.edn codegen + `-main` + scaffolder integration)
- Day 2.5: Live integration test + CI job + smoke

## Deliverables

1. This spec
2. PR-3 plan (next, via writing-plans)
3. Merged PR
4. New CI job recording green

## Open questions

1. **Should `npm run booklogic-compile` run automatically as part of `npm install` (via npm's `prepare` lifecycle hook)?** Recommendation: NO for PR-3. Keep it as an explicit command so developers see what's happening.
2. **What happens if `rules/booklogic/sorts.edn` exists but `rules/booklogic/predicates.edn` is missing?** The compiler treats each file independently: missing = empty list of forms. No error. The detection rule is the *directory* existence, not all three files.
3. **Should the compiler emit the OLD `predicates.edn` or also write a NEW canonical file at `rules/booklogic/.compiled.edn`?** Recommendation: emit only the legacy location for PR-3, so Python keeps working. PR-5 (Bermuda migration) revisits when Bermuda's rules/ becomes BookLogic-sourced. Future BookLogic outputs (atomspace IR, etc.) are in-memory only until PR-5 needs them on-disk for the Rust verifier.
4. **How are nbb's CLJS errors surfaced to the integration test?** stderr piped to the Python test; test asserts the exit code AND searches stderr for any "Error:" / "Exception:" prefixes. Acceptable for v0.4.
