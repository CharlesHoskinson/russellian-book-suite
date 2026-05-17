# BookLogic v0.4 mission — Design

Date: 2026-05-14
Author: Charles
Status: Draft, pending user approval
Supersedes: PR-2 and PR-3 of `2026-05-14-neurosym-forge-v0.3-mission-design.md`

## Problem

The v0.2 + v0.3 pipeline has a structural seam: the "EDN" boundary between Python ingestion and the ClojureScript orchestrator is JSON-pretending-to-be-EDN. `_io.write_json_as_edn` writes `json.dumps(...)`; `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/core.cljs` reads with `cljs.reader/read-string` (an EDN reader, not a JSON reader); `bridge.cljs` does the same for verdicts returned by the Rust addon. Simple types overlap (numbers, strings, vectors, maps) but EDN keywords like `:parishes-count` become JSON strings `":parishes-count"` — CLJS reads them as strings, not keywords. Every downstream meander pattern that matches on `:keyword` shape will silently miss. The v0.3 PR-2 plan ("run real Z3 against Bermuda") would silently produce wrong verdicts.

A second seam: domain predicates live in three places. `rules/predicates.edn` carries the regex catalog. `scripts/ingest_ledger.py` carries the predicate-to-value coercion. `rust-verifier/src/canonical.rs` carries the Z3 assertion. Adding a new predicate means editing three files in lockstep with no schema enforcing they agree.

A third gap: `book-knowledge` emits a JSONL ledger plus a TriG RDF dataset, but neither artifact is consumable by the CLJS orchestrator as a symbolic event stream. The ingestion pipeline's events (source ingested, claim proposed, claim verified, atom emitted) are reconstructed by the verifier rather than being a first-class artifact.

External review on 2026-05-14 surfaced these three issues and proposed a fix: introduce a small EDN-hosted DSL ("BookLogic") that unifies the three predicate locations into one declarative source, and add a `book-knowledge` exporter that emits ingestion events as real EDN.

## Mission

Ship v0.4 of neurosym-forge: BookLogic DSL + real EDN boundary + ingestion-trace artifact. Migrate Bermuda to the new pipeline. Demonstrate genericity by building the osmotic-pressure verifier on the same DSL. The merged-on-main version of v0.4 supersedes the v0.3 mission's PR-2 and PR-3 — there is no intermediate state where Bermuda runs against the old hand-coded predicates.

Deliverables:

- **D1.** Real EDN at every Python↔CLJS↔Rust boundary. No more JSON-stamped-`.edn`.
- **D2.** `book-knowledge` exports `ingest-trace.edn` — append-only symbolic event stream of every ingestion step.
- **D3.** BookLogic DSL v0.1 with seven form families: `defsort`, `defpredicate`, `deflift`, `defrule`, `defconstraint`, `defquery`, `defremedy`.
- **D4.** Bermuda migrated to BookLogic; ledger + chapter prose verified end-to-end with real Z3; the ch-02 parish-count drift fires as a critical D13 ticket.
- **D5.** `verifiers/osmotic_pressure/` shipped as a BookLogic-built verifier; demonstrates the DSL on a non-book chemistry domain.

## Architecture

```
              ┌─────────────────────────────────────────────────┐
              │ book-knowledge                                  │
              │  raw/ wiki/ claims/ graph/                      │
              │  + NEW: export_symbolic_trace.py                │
              └──────────────────┬──────────────────────────────┘
                                 │
                                 │ ingest-trace.edn (events)
                                 │ ledger.jsonl (state)
                                 ▼
              ┌─────────────────────────────────────────────────┐
              │ verifiers/<workspace>/                          │
              │                                                 │
              │  ┌───────────────────────────────────────────┐ │
              │  │ rules/ (BookLogic source, EDN)            │ │
              │  │   sorts.edn       (defsort)               │ │
              │  │   predicates.edn  (defpredicate)          │ │
              │  │   lifts.edn       (deflift)               │ │
              │  │   rules.edn       (defrule)               │ │
              │  │   constraints.edn (defconstraint)         │ │
              │  │   queries.edn     (defquery)              │ │
              │  │   remedies.edn    (defremedy)             │ │
              │  └───────────────────┬───────────────────────┘ │
              │                      │ readable by both        │
              │            ┌─────────┴───────┐                 │
              │            ▼                 ▼                 │
              │  ┌─────────────────┐ ┌──────────────────────┐ │
              │  │ Python loader   │ │ CLJS expander/       │ │
              │  │ (codegen for    │ │ compiler             │ │
              │  │  ingest_ledger) │ │ - DSL→atomspace IR   │ │
              │  │                 │ │ - lifts→meander      │ │
              │  │                 │ │ - constraints→Z3     │ │
              │  │                 │ │ - queries→Cozo       │ │
              │  └─────────────────┘ └──────────┬───────────┘ │
              │                                  │             │
              └──────────────────────────────────┼─────────────┘
                                                 │
                                                 │ real EDN
                                                 ▼
              ┌─────────────────────────────────────────────────┐
              │ rust-verifier/                                  │
              │   ir.rs (real edn-rs parser)                    │
              │   smt.rs (Z3 walk, axioms hook)                 │
              │   axioms.rs (auto-generated from constraints)   │
              └──────────────────────┬──────────────────────────┘
                                     │ verdict.edn (real EDN)
                                     ▼
              ┌─────────────────────────────────────────────────┐
              │ verdict_to_qa.py                                │
              │   verdict.edn → verification-defects.json       │
              └──────────────────────┬──────────────────────────┘
                                     │
                                     ▼
                              book-qa D13
```

BookLogic source files (the `rules/*.edn` set) are the single source of truth. CLJS does the heavy compilation; Python reads the same files for codegen (predicate→regex map for `ingest_ledger.py`). The Rust `canonical.rs` / `axioms.rs` becomes a generated artifact, not a hand-edited file.

## D1 — Real EDN boundary

The fix:

1. Replace `_io.write_json_as_edn` with `write_edn` that emits actual EDN syntax:
   - Map keys without quotes when they are keyword-shaped (`:foo`)
   - Vectors with `[...]`, maps with `{...}`, lists with `(...)` only where the BookLogic syntax requires
   - Keywords without surrounding quotes
2. Add `read_edn` in Python that uses a tiny EDN reader. For v0.4 we ship a hand-rolled reader good enough for our subset (no tagged literals, no records, no custom dispatch). Roughly 150 lines of Python.
3. CLJS continues to use `cljs.reader/read-string`; no CLJS changes for this fix.
4. Rust side: replace `serde_json::from_str` on the input side with `edn-rs`. Replace `serde_json::to_string` on the verdict side with manual EDN emission (or a small `edn-rs` writer).

After the fix, the round-trip is: Python writes `{:kind :expression :id "C001" :predicate :parishes-count :subject :Bermuda :value 9}` → CLJS reads keywords as keywords → Rust reads via `edn-rs` → Rust emits EDN verdict → CLJS reads keywords as keywords.

The fixture EDN format becomes the canonical artifact format for the entire pipeline. The `.edn` extension finally means what it says.

## D2 — `ingest-trace.edn`

New artifact at `examples/<workspace>/analysis/ingest-trace.edn`. Append-only EDN with shape:

```clojure
{:version 1
 :book/id "bermuda-manual"
 :events
 [(source/ingested
    {:doc/id "bermuda-source-001"
     :kind :pdf
     :sha256 "abcd..."
     :ingested-at #inst "2026-05-12T16:13:51Z"})

  (claim/proposed
    {:claim/id "clm-2026-000001"
     :text "Bermuda has nine traditional parishes."
     :source/spans [{:doc/id "bermuda-source-001"
                     :locator-text "Bermuda has nine traditional parishes."}]
     :confidence 0.82
     :proposed-at #inst "2026-05-12T16:14:01Z"})

  (claim/verified
    {:claim/id "clm-2026-000001"
     :method :locator-text-confirmed
     :verified-at #inst "2026-05-12T16:14:05Z"})

  (atom/emitted
    {:claim/id "clm-2026-000001"
     :form (fact :Bermuda :parishes-count 9)
     :sort :formula
     :provenance [:source/span "bermuda-source-001"]})

  ;; … one event per state transition
  ]}
```

`(source/ingested {...})`, `(claim/proposed {...})`, etc. are EDN lists (S-expressions). The head symbol names the event kind; the tail map carries the payload. The CLJS reader treats them as `(head & args)` lists; the Python reader treats them as `[head args]` tuples. Both can dispatch on `head`.

Produced by a new `book-knowledge/scripts/export_symbolic_trace.py` that reads `claims/ledger.jsonl`, `claims/events.jsonl`, and `raw/manifests/*.json` and emits the unified event stream. Regenerable; the existing JSONL ledger remains the authoritative source.

Consumed by the verifier as the Phase-1 input (replacing the current direct read of `ledger.jsonl`).

## D3 — BookLogic DSL v0.1

Seven form families. All forms are EDN lists with a head symbol from the BookLogic namespace.

### `defsort`

Declares a sort (type) in the atomspace.

```clojure
(defsort :entity)
(defsort :claim)
(defsort :source)
(defsort :span)
(defsort :formula)
(defsort :verdict)
(defsort :int)        ;; primitives may be redeclared as identity (no-op)
(defsort :real)
(defsort :bool)
(defsort :string)
```

Compiles to entries in the existing `rules/seed.edn` sort registry.

### `defpredicate`

Declares a typed predicate.

```clojure
(defpredicate :parishes-count [:entity] :int)
(defpredicate :currency-pegged-at-parity [:entity] :bool)
(defpredicate :airport-on-island [:entity] :entity)
(defpredicate :binomial [:entity] :string)
(defpredicate :population [:entity] :int)
```

Compiles to entries in `predicates.edn` (the codegen target Python reads).

### `deflift`

Lifts text or ledger data into typed atoms via a regex pattern.

```clojure
(deflift L001-parish-count
  :from :claim/canonical-text
  :when #"(?i)(?<n>\d+|nine|eight|seven)\s+(traditional\s+)?parishes?"
  :emit (fact ?claim-id :parishes-count :Bermuda (parse-int ?n))
  :word-to-int {"nine" 9 "eight" 8 "seven" 7}
  :provenance :inherit
  :confidence :inherit)
```

- `:from` — which slot of the source claim to scan
- `:when` — EDN-readable regex (compiled by both Python and CLJS readers)
- `:emit` — the atom form to produce; named-capture groups become bound variables
- `:word-to-int` (optional) — map English number words to ints
- `:provenance` and `:confidence` — default `:inherit` (copy from the source claim)

Compiles to:
- CLJS: a meander rewrite clause
- Python: a regex entry in the generated predicates map for `ingest_ledger.py` and `extract_prose.py`

### `defrule`

Term-rewrite rule for atomspace normalization.

```clojure
(defrule R001-normalize-st-davids
  (= (entity "St. David's Island")
     :St_Davids_Island)
  :tags [:normalization :entity])

(defrule R002-celsius-to-kelvin
  (= (apply :temperature ?s)
     (+ (apply :temperature-celsius ?s) 273.15))
  :tags [:algebraic :unit-conversion])
```

Same shape as the existing `rules/rules.edn` from v0.2; the only change is the DSL wrapper. Compiles to meander rewrite rules in CLJS; Python doesn't need to consume these.

### `defconstraint`

Solver-backend assertion.

```clojure
(defconstraint C001-bermuda-parishes
  :backend :z3
  :assert (= (:parishes-count :Bermuda) 9)
  :track :claim/id
  :on-unsat {:defect :D13
             :severity :critical
             :message "Claim contradicts canonical Bermuda parish count."})
```

- `:backend` — `:z3` for now; `:egg` for equality saturation; `:cozo` for Datalog
- `:assert` — the formula to assert (in the atomspace IR)
- `:track` — what tracker name to use (`:claim/id` means use the source claim's id; alternatives: a literal tracker name)
- `:on-unsat` — book-qa defect ticket to emit if this constraint participates in the unsat core

Compiles to Z3 `assert_and_track` calls in the generated `axioms.rs`. The hand-edited `canonical.rs` is replaced by generated `axioms.rs` for the standard constraints; project authors only edit BookLogic source.

### `defquery`

Datalog query for analysis gates.

```clojure
(defquery Q001-low-confidence-load-bearing
  :backend :cozo
  :find [?claim]
  :where [(claim/load-bearing ?claim true)
          (claim/posterior ?claim ?p)
          (< ?p 0.80)]
  :on-result {:defect :posterior-floor
              :severity :warning})
```

Compiles to a CozoDB query in the verifier's `kg.rs` (currently a stub; v0.4 wires this up). Results become defect tickets in `book-qa`.

### `defremedy`

Writeback proposal triggered by a verdict pattern.

```clojure
(defremedy W001-unsat-core-to-refutation
  :when (unsat-core ?claim)
  :propose (ledger/transition ?claim :refuted)
  :requires :human-review)
```

Compiles to entries in `book-qa.scripts.propose_writeback.py`'s rule list. `:requires :human-review` means the proposal doesn't auto-apply.

### Reader behaviour

- CLJS uses `cljs.reader/read-string` for EDN parsing. The DSL forms are lists; the CLJS expander dispatches on the head symbol (`defsort`, `defpredicate`, etc.).
- Python ships a small reader (`scripts/_edn_reader.py` in neurosym-forge) good enough to parse our subset. It returns `(head, args)` tuples; a thin compiler in Python codegen-maps the predicate-bearing forms (`defpredicate`, `deflift`) into the regex table `ingest_ledger.py` consumes.
- Rust uses `edn-rs` for parsing both input atoms and any DSL forms it needs (constraints, ultimately).

## D4 — Bermuda migration

After D1-D3 land, Bermuda's `rules/` directory becomes:

```
verifiers/bermuda/rules/
├── sorts.edn        (defsort ...)
├── predicates.edn   (defpredicate ...)  ; now generated from BookLogic source, not hand-written
├── lifts.edn        (deflift ...)       ; replaces the regex catalog in scripts/prose_patterns.py
├── rules.edn        (defrule ...)       ; existing rewrite rules, wrapped
├── constraints.edn  (defconstraint ...) ; replaces canonical.rs hand-written axioms
├── queries.edn      (defquery ...)      ; new — exercises the Cozo backend
├── remedies.edn     (defremedy ...)     ; new — feeds book-qa.propose_writeback
└── .checksums.edn   (unchanged)
```

`rust-verifier/src/canonical.rs` is removed. Its contents are regenerated as `rust-verifier/src/axioms.rs` from the BookLogic `defconstraint` forms during scaffold-or-update.

`scripts/prose_patterns.py` becomes a thin wrapper that loads the regex table generated from `lifts.edn`.

End-to-end test: scaffolded project builds, ingests Bermuda's ledger via the new symbolic trace, extracts prose, runs Z3 with the generated axioms, and returns `:unsat` with the ch-02 parish-count atom in the unsat core. The D13 ticket fires.

Quantitative claim expansion (the original v0.3 PR-2 sub-deliverable) lands here too: four new `defpredicate` + `defconstraint` pairs for population, land-area-km2, gdp-usd-billion, hospital-beds-kemh.

### Closure note (2026-05-17)

PR-5 (`feat/booklogic-pr5`) landed § D4. Concretely:

- `verifiers/bermuda/rules/booklogic/` now hosts seven BookLogic source files (`sorts.edn`, `predicates.edn`, `lifts.edn`, `rules.edn`, `constraints.edn`, `queries.edn`, `remedies.edn`).
- `rust-verifier/src/canonical.rs` is deleted; `rust-verifier/src/axioms.rs` is generated from `constraints.edn` and checked in; `test_axioms_lockstep.py` enforces byte-identical regeneration.
- The five canonical predicates plus four new quantitative predicates (`population`, `land-area-km2`, `gdp-usd-billion`, `hospital-beds-kemh`) ship in the codegened regex table that `prose_patterns.py` and `ingest_ledger.py` consume.
- `examples/bermuda-manual/claims/ledger.jsonl` carries four new appended claims (`clm-2026-000011` through `clm-2026-000014`).
- Two new CI jobs on `ubuntu-latest`: `bermuda-z3-build` (cargo build with the `smt` feature) and `bermuda-z3-verify` (end-to-end real-Z3 run; asserts D13 ticket fires for the ch-02 parish-count drift).
- `tests/test_run_verification.py` confirms `stub_verifier=False` is the default; the stub remains for fast local iteration via explicit opt-in.

Plan: `docs/plans/2026-05-17-booklogic-pr5.md`.

## D5 — osmotic-pressure showcase

`verifiers/osmotic_pressure/` shipped entirely via BookLogic source. No Python-or-Rust hand-edits beyond what BookLogic generates. The BookLogic source for the project is roughly:

```clojure
;; sorts.edn
(defsort :solution)

;; predicates.edn
(defpredicate :osmotic-pressure-pa [:solution] :real)
(defpredicate :vant-hoff-i         [:solution] :real)
(defpredicate :molarity            [:solution] :real)
(defpredicate :temperature-k       [:solution] :real)

;; constraints.edn  (van 't Hoff with 3% tolerance)
(defconstraint C001-vant-hoff
  :backend :z3
  :assert (~= (:osmotic-pressure-pa ?s)
              (* (:vant-hoff-i ?s) (:molarity ?s) 8.314 (:temperature-k ?s))
              :tolerance 0.03)
  :on-unsat {:defect :D13 :severity :critical
             :message "van 't Hoff equation violated"})
```

Two fixture ledgers:
- `claims_clean.jsonl` — i=2, M=0.154, T=298.15, π=780202.5 → expect `:sat`
- `claims_doctored.jsonl` — i=1 (same M, T, π) → expect `:unsat` with the offending claim in the core

Demonstrates the DSL is reusable beyond Bermuda; demonstrates the `~=` (approximate equality) operator works.

## Sub-PR slate

Six sub-PRs:

```
PR-1  EDN boundary fix                                 ~1.5 days
  - real EDN writer + reader in Python
  - edn-rs in Rust (replaces serde_json on input/verdict paths)
  - CLJS unchanged (already EDN-correct)
  - migrate existing Bermuda + neurosym-forge fixtures to real EDN
  - 12-15 new tests

PR-2  ingest-trace exporter                            ~1 day
  - book-knowledge/scripts/export_symbolic_trace.py
  - event schema in book-knowledge/assets/events.schema.json (already exists; extend)
  - 6-8 new tests

PR-3  BookLogic core (defsort, defpredicate, deflift)  ~2.5 days
  - Python reader scripts/_edn_reader.py in neurosym-forge
  - CLJS expander cljs-orchestrator/src/main/<slug>/dsl.cljs
  - Codegen: BookLogic source → predicates.edn (Python-consumable map)
  - 15-20 new tests

PR-4  BookLogic full (defrule, defconstraint, defquery, defremedy) ~2.5 days
  - Constraint codegen → axioms.rs in Rust
  - Query backend → Cozo (replaces existing kg.rs stub)
  - Remedy backend → book-qa.propose_writeback feeder
  - 20-25 new tests

PR-5  Bermuda migration + real Z3 run                  ~2 days
  - Bermuda rules/* migrated from hand-edited to BookLogic source
  - canonical.rs deleted; axioms.rs generated
  - 4 new quantitative predicates (population, land-area, GDP, hospital-beds)
  - Cargo build, Z3 link, real run, verification-report v0.2
  - book-qa D13 fires on ch-02 drift

PR-6  Osmotic-pressure showcase                        ~1.5 days
  - verifiers/osmotic_pressure/ entirely via BookLogic source
  - clean + doctored fixture ledgers
  - CI smoke job asserts :sat and :unsat verdicts
```

Total: ~11 days across six PRs.

Each PR is independently reviewable. Between PRs the controller re-brainstorms with the user, adjusting the next PR's plan based on what landed.

## Workspace mutation policy

PR-1 touches `_io.py` (neurosym-forge), `ir.rs.tmpl`/`smt.rs.tmpl`/Cargo.toml.tmpl (template diff), Bermuda's existing rules + fixtures.

PR-2 touches `book-knowledge/` only (new exporter + tests + schema extension). The existing `claims/` ledger and `events.jsonl` are read-only.

PR-3 touches `neurosym-forge/` (new Python reader, new CLJS expander module in template, codegen scripts). No book-knowledge or book-qa changes.

PR-4 touches `neurosym-forge/` templates (constraints/queries/remedies codegen). Touches `book-qa.scripts.propose_writeback.py` to accept BookLogic-generated proposals.

PR-5 touches `verifiers/bermuda/` heavily (rules/* rewritten as BookLogic source; canonical.rs deleted; prose_patterns.py becomes a thin wrapper). Touches `examples/bermuda-manual/claims/ledger.jsonl` (append-only adds for the four quantitative claims).

PR-6 creates `verifiers/osmotic_pressure/`. No other touches.

No skill ownership boundaries are crossed. `book-knowledge` adds a new artifact under its own tree; the `claims/` ledger stays append-only and the existing JSONL format remains authoritative.

## Non-goals

- A full theorem prover. BookLogic is a declarative layer over existing backends (Z3, Cozo); it does not introduce a new solver.
- A general-purpose Lisp dialect. BookLogic is seven form families and a fixed EDN subset.
- Replacing `book-knowledge`'s authoritative ingestion. The exporter is purely derivative.
- Replacing `cljs.reader`. CLJS keeps the standard reader.
- WASM Rust build, cvc5 second-opinion, book-thesis entailment loop — still v0.5+.
- A Python compiler equivalent to CLJS. Python only reads BookLogic source for codegen; the full expander stays in CLJS.

## Open questions

1. **Approximate equality.** `defconstraint` for the van 't Hoff law needs `~=` with a tolerance. Z3's real arithmetic supports this directly via `|a - b| ≤ ε`. We codegen the desugaring in PR-4. No design open question; deferred to PR-4 implementation.

2. **Schema for ingest-trace events.** Should events be open (any head symbol allowed) or closed (fixed enum of `source/ingested`, `claim/proposed`, etc.)? Recommendation: closed in v0.4 with `book-knowledge/assets/events.schema.json` enumerating valid heads. Reopened in v0.5 if downstream skills need to emit custom event kinds.

3. **Editing BookLogic source by hand vs through helper scripts.** The existing checksum policy (`.checksums.edn`) enforces "only `add_*` helpers edit `rules/*.edn`". With BookLogic, the source files are larger and authoring-by-hand is more natural. Proposed: keep checksums for `predicates.edn` (since that's now codegen-only) but allow direct edits to `lifts.edn`, `constraints.edn`, etc. with a looser policy (lint warns on uncheckable edits but doesn't block).

4. **Bidirectional traceability.** When a Z3 unsat core surfaces a tracker, we need to map back from the tracker name to (a) the BookLogic constraint that generated the assertion, (b) the original claim ID, and (c) the source span. PR-4 builds this via a generated lookup table emitted alongside `axioms.rs`. Concrete design happens in PR-4's plan.

5. **CI build feasibility for Rust + Z3.** The v0.3 spec flagged the bundled Z3 build (cmake + C++ toolchain) as possibly not buildable on this machine. PR-5 either ships a working local build or moves the real-verify step to GitHub Actions ubuntu-latest. Decision deferred until PR-5 dev work starts.

## Estimated effort total

11 days across 6 PRs. Five review checkpoints between PRs allow course correction.

## Deliverables

- This file (`docs/specs/2026-05-14-booklogic-v0.4-mission-design.md`)
- Six tactical plans written between PR landings
- Six merged PRs
- A `references/booklogic-dsl.md` reference doc as part of PR-3
- The documentation handoff brief from PR #23 covers v0.3; an addendum for v0.4 may be issued after the mission lands

## Closure log

- **PR-4 (D4) — BookLogic active forms landed 2026-05-17.** Four expanders (`defrule`, `defconstraint`, `defquery`, `defremedy`) ship in `booklogic.cljs.tmpl`. Each form family has its own intermediate EDN target plus a Python codegen pass (axioms.rs from constraints.edn; kg.rs from queries.edn) or a downstream consumer (book-qa.propose_writeback for remedies). Open question #1 (~= approximate-equality) implemented with :tolerance e desugaring to |LHS - RHS| <= e. Open question #4 (bidirectional traceability for Z3 unsat cores) solved via `rules/axioms-tracker-map.edn`. Open question #5 (Z3 bundled build on Windows) deferred to PR-5; PR-4 cargo-check gate runs on ubuntu-latest.

