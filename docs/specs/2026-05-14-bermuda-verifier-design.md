# bermuda-verifier — Design

Date: 2026-05-14
Author: Charles
Status: Draft, pending user approval

## Problem

The Bermuda manual has gone through six review cycles (v3 → v6). Each cycle surfaced cross-chapter contradictions that human and persona reviewers caught and that `canonical-facts.md` then arbitrated: "around 180 islands" vs "181 named islands", parish counts that drifted between 8 and 9, airport-location confusions, hospital bed counts that varied by chapter. These contradictions are deterministic to detect once the canonical facts are stated, but the existing pipeline only catches them at review time.

The ledger today is logically consistent — the three `fact`-class entries (`clm-2026-000008`, `000009`, `000010`) restate canonical-facts.md as policy and no other claim contradicts them. The risk lives in the *prose*: a chapter draft can say "around 180 islands" even though the ledger says "181 named islands and rocks". The book-qa Stage-1 linter (D1–D8) detects orphan citation tokens and markdown bleed; D9–D12 from book-thesis detect entailment failures over the claim graph; nothing detects when chapter prose carries a numeric or named-entity claim that contradicts a canonical fact.

The `neurosym-forge` skill landed in PR #14 with a deferred `--book-knowledge-bridge` integration. The bridge is the v0.2 milestone. The Bermuda manual is the natural first workspace to wire it against.

## What v0.2 ships

A new project at `verifiers/bermuda/` produced by `neurosym-forge`'s scaffolder, plus three new scripts inside it that the scaffold did not previously emit, plus a `book-qa` defect class **D13** that consumes the verifier's verdict.

End-to-end flow:

```
       ┌─────────────────────────┐
       │ book-knowledge           │
       │  claims/ledger.jsonl     │  ── 46 claims, 12 facts
       └──────────────┬───────────┘
                      │ Phase 1 ingest
                      ▼
       ┌─────────────────────────┐
       │ verifiers/bermuda/       │
       │  scripts/ingest_ledger   │  EDN atomspace, sort-typed
       │  → work/claims.edn       │
       └──────────────┬───────────┘
                      │
       ┌──────────────┴───────────┐
       │ book-compose             │
       │  book/releases/N.N.N/    │
       │   chapter-bundles/*/     │
       │   draft.md               │
       └──────────────┬───────────┘
                      │ Phase 1b extract
                      ▼
       ┌─────────────────────────┐
       │ verifiers/bermuda/       │
       │  scripts/extract_prose   │  numeric + named-entity facts
       │  → work/prose-facts.edn  │  per chapter
       └──────────────┬───────────┘
                      │ Phase 2: CLJS rewrite
                      ▼
       ┌─────────────────────────┐
       │ verifiers/bermuda/       │
       │  cljs-orchestrator       │  meander: claim → FOL formula
       │  → work/fol.edn          │
       └──────────────┬───────────┘
                      │ napi-rs
                      ▼
       ┌─────────────────────────┐
       │ verifiers/bermuda/       │
       │  rust-verifier           │  Z3: canonical-facts hard
       │                          │  constraints + ledger atoms +
       │                          │  prose facts (tracked)
       │  → work/verdict.edn      │  cozo: contradiction scan
       └──────────────┬───────────┘
                      │ verdict.edn → JSON for book-qa
                      ▼
       ┌─────────────────────────┐
       │ book-qa                  │
       │  lint_artifact.py        │  D13: claim-set unsatisfiable
       │  qa/verification-        │  → reads work/verdict.json
       │      defects.json        │  → emits D13 ticket per unsat
       └─────────────────────────┘  →   core member
```

The flow runs whenever `book-qa` runs Stage-1. Missing `work/verdict.json` is not an error — D13 is skipped gracefully, matching the existing pattern for D9–D12.

## Components

### 1. `verifiers/bermuda/` — scaffolded project

Produced by `neurosym-forge.scripts.scaffold_project --slug bermuda --book-knowledge-bridge`. The bridge flag emits the three scripts below in addition to the standard CLJS+Rust skeleton.

The scaffold pre-populates `rules/seed.edn` with the canonical-facts as `(=)` rules (see § "Canonical facts as Z3 constraints"). Subsequent canonical-fact additions go through `add_rewrite_rule` so the checksum chain stays intact.

### 2. `verifiers/bermuda/scripts/ingest_ledger.py`

Reads `examples/bermuda-manual/claims/ledger.jsonl` via `book-knowledge`'s `io_utils.read_jsonl` and `latest_per`. For each claim with `tbf:status: verified` or `status: verified`, emits an expression atom into `work/claims.edn`.

Translation rules:
- A claim with `claim_type: fact` and a textual canonical statement becomes an opaque assertion atom. The first pass uses string-matching against the canonical-facts predicate map; everything that doesn't match goes through as an `:OPAQUE` atom and is ignored by the verifier.
- A claim with `claim_type: design_decision` is treated as ledger context, not an asserted fact. Design decisions describe what the manual *says*, not what is *true*; they go into the atomspace as `:context` atoms that the verifier can reference for provenance but does not check.
- `supports_chapters` becomes a `:supports` predicate edge in the cozo store.

The predicate map (initial, expandable): `parishes(Bermuda) = N`, `currency_pegged(BMD, USD) = parity`, `airport_location(LF_Wade) = St_Davids_Island`, `island_count_named(Bermuda) = N`, `cedar_binomial(Bermuda_cedar) = "Juniperus bermudiana"`.

### 3. `verifiers/bermuda/scripts/extract_prose.py`

Runs over each chapter draft in `examples/bermuda-manual/book/releases/N.N.N/chapter-bundles/ch-NN/draft.md`. Extracts facts in two passes:

**Pass A — deterministic regex.** Looks for patterns that previous review cycles surfaced as drift-prone:
- `(\d+)\s+(islands?|named islands?|islands and rocks)`
- `(\d+|nine|eight)\s+(traditional|major)?\s*parishes?`
- patterns for hospital-bed counts, population figures, total land area in km², airport runway length.

The regex catalog lives in `verifiers/bermuda/scripts/prose_patterns.py` and is grown incrementally as new drift classes are observed.

**Pass B — LLM extraction.** A `Callable[[str], str]` is parameterized (the project's `pyproject.toml` declares no LLM dependency; the harness passes the callable in). The prompt asks for "all numeric claims and named entities in this chapter, as JSON with `predicate`, `subject`, `value`, `unit` fields." The output is reconciled against the predicate map; predicates not in the map are recorded but not constrained by the verifier.

Pass A is mandatory and runs in the standard `book-qa` flow. Pass B is opt-in via `examples/<workspace>/qa-config.yaml`'s `enable_prose_llm_extraction: true` field; the workspace defaults to `false`.

### 4. Verifier extensions

The scaffolded Rust verifier inherits the standard Z3 / egg / cozo / tectonic stubs. The bermuda-specific additions:

- `rust-verifier/src/canonical.rs` — encodes canonical facts as Z3 hard constraints (not tracked, not in the unsat core). These are *axioms* of the verification: a contradiction with a canonical fact is by definition a defect in the ledger or prose.
- `rust-verifier/src/smt.rs` — every ledger and prose atom is wrapped with `assert_and_track` so the unsat core points to the offending atom by ID.
- `rust-verifier/src/kg.rs` — cozo Datalog includes a new query `parishes_contradiction` that finds any prose-fact whose value disagrees with the canonical assertion, even if Z3 didn't surface it (defense in depth).

### 5. `book-qa` D13 hook

A new linter in `skills/book-qa/scripts/lint_artifact.py`:

- **D13** claim-set-unsatisfiable — Z3 returned `:unsat` on the verified-claim + prose-fact set.
  - Severity: `critical` (factual integrity is non-negotiable)
  - Read from `<workspace>/qa/verification-defects.json` if it exists
  - Only `verdict: "unsat"` produces tickets; `:sat` is silent and `:unknown` is logged but does not gate
  - One ticket per claim ID in the unsat core
  - Missing file → D13 skipped (matches D9–D12 pattern)

The verification-defects.json shape:
```json
{
  "verdict": "sat" | "unsat" | "unknown",
  "core": ["clm-2026-000008", "prose-ch-04-001", ...],
  "explanation": "Chapter 4 prose says 8 parishes; canonical fact requires 9.",
  "produced_at": "2026-05-14T...",
  "verifier_version": "bermuda 0.1.0 / neurosym-forge 0.2.0"
}
```

The `book-qa` Stage-1 linter is the only consumer. The healer (Stage 4) can patch chapter prose based on D13 tickets when the verdict's `core` includes a prose-fact ID (recoverable); ledger contradictions are not auto-patched (would require ledger ownership transfer, which violates the book-knowledge invariant).

## Canonical facts as Z3 constraints

Each fact in `canonical-facts.md` becomes a Z3 axiom. Concrete encoding for the six current facts:

```rust
// In rust-verifier/src/canonical.rs

// Island count
let bermuda = ctx.const_("Bermuda", &entity_sort);
let island_count = func_decl_named_islands_and_rocks(&ctx);
solver.assert(&island_count.apply(&[&bermuda])._eq(&Int::from_i64(&ctx, 181)));

// Parish count
let parishes = func_decl_traditional_parishes(&ctx);
solver.assert(&parishes.apply(&[&bermuda])._eq(&Int::from_i64(&ctx, 9)));

// Parish names (an enum)
let parish = z3::DatatypeBuilder::new(&ctx, "Parish")
    .variant("Sandys", vec![]).variant("Southampton", vec![])
    .variant("Warwick", vec![]).variant("Paget", vec![])
    .variant("Pembroke", vec![]).variant("Devonshire", vec![])
    .variant("Smiths", vec![]).variant("Hamilton", vec![])
    .variant("StGeorges", vec![]).finish();
// (Membership constraints emitted as forall over Parish.)

// Currency pegging
let bmd = ctx.const_("BMD", &currency_sort);
let usd = ctx.const_("USD", &currency_sort);
let pegged_at = func_decl_pegged_at(&ctx);
solver.assert(&pegged_at.apply(&[&bmd, &usd])._eq(&Real::from_real(&ctx, 1, 1)));

// Airport location
let lfw = ctx.const_("L_F_Wade", &airport_sort);
let on_island = func_decl_on_island(&ctx);
let in_parish = func_decl_in_parish(&ctx);
solver.assert(&on_island.apply(&[&lfw])._eq(&ctx.const_("St_Davids_Island", &island_sort)));
solver.assert(&in_parish.apply(&[&lfw])._eq(&parish.variant("StGeorges")));

// Cedar binomial
let cedar = ctx.const_("Bermuda_cedar", &species_sort);
let binomial = func_decl_binomial(&ctx);
solver.assert(&binomial.apply(&[&cedar])._eq(&z3::ast::String::from_str(&ctx, "Juniperus bermudiana")));
```

The hospital bed count and population are left as **soft constraints** in v0.2 because the source documents don't pin a single number; they're parameterized by year. The verifier reports `:unknown` on those if a prose-fact disagrees with the ledger; future ledger growth will tighten them.

## Ledger ingestion contract

`ingest_ledger.py` maps the JSONL claim shape to EDN atoms:

| Ledger field | Atom mapping |
|---|---|
| `claim_id` | `:id` on the expression atom |
| `claim_type: fact` | atom becomes an `assert_and_track`-eligible expression |
| `claim_type: design_decision` | atom emitted as `:context` (provenance only) |
| `canonical_text` | parsed through the predicate map; if no match, emitted as `:OPAQUE` |
| `status: verified` or `tbf:status: verified` | required for inclusion; non-verified claims skipped |
| `source_spans[]` | `:source` metadata on the atom |
| `supports_chapters[]` | cozo edges `(claim-id, :supports, ch-NN)` |
| `confidence` | `:confidence` metadata (informational) |

Schema validation: the ingester runs `book-knowledge.scripts.claim_validator.validate(claim)` on each row before translation. A schema failure stops ingestion with a clear error.

## Prose-fact extraction contract

`extract_prose.py` reads each `chapter-bundles/ch-NN/draft.md` and emits atoms with IDs like `prose-ch-04-001`. The atom shape mirrors a ledger fact:

```clojure
{:kind :expression
 :id "prose-ch-04-001"
 :sort :formula
 :doc "ch-04 paragraph 7 — 'around 180 islands'"
 :source {:file "ch-04/draft.md" :line 142}
 :head {:kind :symbol :name :island-count-named :sort :rule}
 :args [{:kind :symbol :name :Bermuda :sort :entity}
        {:kind :grounded :sort :int :name :literal :grounded {:lib "literal" :fn "value"}}]
 :confidence 0.7}  ; lower confidence for prose-extracted than ledger
```

Pass A (regex) emits with `:confidence 0.9`. Pass B (LLM) emits with `:confidence 0.6` and `:extractor :llm`. The verifier weights both equally in unsat-core membership; confidence informs the healer's patch suggestions only.

## Project layout

```
verifiers/                                    NEW directory at repo root
└── bermuda/                                  scaffolded by neurosym-forge
    ├── SKILL.md                              standard scaffold output
    ├── README.md
    ├── package.json, shadow-cljs.edn, deps.edn
    ├── Cargo.toml
    ├── rules/
    │   ├── seed.edn                          canonical facts as rewrite rules
    │   ├── grounded.edn                      z3-check-all, egg-saturate, etc.
    │   ├── predicates.edn                    NEW: predicate map for ledger ingestion
    │   ├── .checksums.edn
    │   └── .forge-version.edn
    ├── cljs-orchestrator/                    standard scaffold + bermuda phases
    ├── rust-verifier/
    │   └── src/
    │       ├── ... (standard scaffold)
    │       └── canonical.rs                  NEW: Bermuda hard constraints
    ├── scripts/                              NEW: bermuda-specific Python helpers
    │   ├── __init__.py
    │   ├── ingest_ledger.py                  ledger.jsonl → claims.edn
    │   ├── extract_prose.py                  chapter drafts → prose-facts.edn
    │   ├── prose_patterns.py                 regex catalog
    │   ├── verdict_to_qa.py                  verdict.edn → verification-defects.json
    │   └── run_verification.py               orchestrator: ingest → build → verify
    └── tests/
        ├── test_ingest_ledger.py
        ├── test_extract_prose.py
        ├── test_canonical_constraints.py     synthetic unsat cases
        ├── test_verdict_to_qa.py
        └── fixtures/
            ├── ledger_clean.jsonl            current 46-claim Bermuda ledger
            ├── ledger_with_contradiction.jsonl
            ├── chapter_clean.md
            └── chapter_with_8_parishes.md
```

The `verifiers/` directory at repo root is new. Per `CLAUDE.md` it sits parallel to `skills/` and `examples/`. It is not owned by any existing skill (book-knowledge does not write there; neurosym-forge produces it).

## `neurosym-forge` v0.2 changes

This work also lands the deferred `--book-knowledge-bridge` flag in `neurosym-forge`. The flag re-emerges as a real feature:

- `scripts/scaffold_project.py` accepts `--book-knowledge-bridge` again
- When set: emits `scripts/ingest_ledger.py` (the project's own ingester template) and seeds `rules/predicates.edn` with placeholder predicates
- The Bermuda scaffold uses this flag

The neurosym-forge SKILL.md updates to reflect this. The "v0.2 only" deferral notes are removed.

## Workspace mutation policy

Per `CLAUDE.md`: "book-knowledge is the only writer of `claims/`, `wiki/`, `raw/`, `graph/`". This work does not violate the rule:

- `verifiers/bermuda/` writes only to `verifiers/bermuda/work/` and `verifiers/bermuda/rules/` (its own tree).
- It READS from `examples/bermuda-manual/claims/ledger.jsonl` and `examples/bermuda-manual/book/releases/N.N.N/chapter-bundles/`.

The `qa/` directory has an established external-tool carve-out: `book-thesis` already writes `qa/supports-defects.json`, `qa/datalog-defects.json`, and `qa/entailment-results.json` for `book-qa.lint_artifact.py` to consume. `bermuda-verifier` follows the same pattern: it writes `qa/verification-defects.json` (and only that file) for D13 to read. The authoritative `qa/defects.json` aggregate stays book-qa's.

## Testing strategy

Three test surfaces:

1. **Unit tests** in `verifiers/bermuda/tests/` cover the ingester, extractor, and verdict translator. ~25 tests.
2. **Integration test** in `skills/book-qa/tests/test_lint_artifact.py`: D13 reads a synthetic `verification-defects.json` and emits a critical defect. Test with both `:sat` (no defect) and `:unsat` (one defect per core member) verdicts.
3. **End-to-end smoke** in `verifiers/bermuda/tests/test_end_to_end.py`: scaffold a temp project, run ingest → (mock the Rust verifier with a stub) → run verdict_to_qa → assert book-qa picks up D13. The Rust side is not actually built in tests; the stub returns a fixture verdict.

The end-to-end test does **not** build CLJS or Rust because the dependency surface (shadow-cljs, cargo, napi-rs, Z3) is too heavy for CI. A separate `make verify-bermuda` target in the repo's top-level Makefile (or a one-off `tools/verify_bermuda.sh` script) covers the full build path for manual verification.

## Non-goals (v0.2)

- Automated ledger writeback: if the verifier finds the ledger itself is inconsistent (not the prose), it emits a ticket but does not propose a ledger transition. That goes through `book-qa`'s existing `propose_writeback.py` if at all.
- WASM build of the Rust verifier — still v0.3.
- cvc5 second-opinion solver — still v0.3.
- Verifier-driven chapter regeneration loop — out of scope; the healer is allowed to patch prose but does not re-run the verifier in a tight loop (max 1 iteration per chapter).
- Verifying non-Bermuda workspaces — the scaffold is reusable, but no other example workspace is wired up in this PR.

## Estimated effort

- `neurosym-forge` v0.2 changes (re-add `--book-knowledge-bridge`, template additions): 0.5 day
- `verifiers/bermuda/` scaffold + canonical.rs + smt.rs Bermuda-specific code: 1.5 days
- `ingest_ledger.py` + `extract_prose.py` (pass A regex only) + tests: 1 day
- `extract_prose.py` pass B (LLM) + tests: 1 day
- `verdict_to_qa.py` + `book-qa` D13 hook + tests: 1 day
- End-to-end integration smoke + manual full-stack verification on real Bermuda corpus: 0.5 day
- Documentation pass (`docs/operations/`, `examples/bermuda-manual/reports/verification-report.md`): 0.5 day

Total: **5-6 days** for one engineer familiar with both stacks. The long pole is the canonical.rs encoding — getting Z3 sorts and quantifier patterns right for the mixed-arity predicates takes iteration.

## Deliverables

1. `docs/specs/2026-05-14-bermuda-verifier-design.md` (this file)
2. `docs/plans/2026-05-14-bermuda-verifier.md` (TDD plan)
3. `skills/neurosym-forge/` v0.2 changes (re-add `--book-knowledge-bridge`)
4. `verifiers/bermuda/` (new directory, scaffolded + extended)
5. `skills/book-qa/scripts/lint_artifact.py` (new D13 linter)
6. `skills/book-qa/tests/test_lint_artifact.py` (D13 tests)
7. `examples/bermuda-manual/reports/verification-report.md` (regenerable artifact)
8. README updates: `verifiers/` directory documented; `neurosym-forge` row updated to remove the "deferred to v0.2" note.

## Open questions

1. **Where does `run_verification.py` get invoked?** Recommendation: a new `book-qa` Stage-0 step that runs `verifiers/<slug>/scripts/run_verification.py` if a matching `verifiers/<slug>/` exists for the workspace, *before* Stage-1's `lint_artifact.py`. Default off; enabled per workspace via `qa-config.yaml: enable_verification: true`. This keeps the dependency on Rust/CLJS toolchains opt-in.
2. **Should the verifier run on the released bundle or the chapter sources?** Decision: chapter sources (`book/releases/N.N.N/chapter-bundles/ch-NN/draft.md`), so a prose-fact tied to a draft is patchable by the healer without re-rendering the bundle.
3. **What's the v0.3 path?** Quantitative ledger growth (population, GDP, hospital beds with dated values); WASM build; cvc5 second opinion; verifier-driven entailment loop with book-thesis.
