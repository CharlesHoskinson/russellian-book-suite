# BookLogic v0.4 — Claude-only finish — Design

**Date:** 2026-05-17
**Author:** Charles
**Status:** Draft, pending user approval
**Supersedes:** The two-agent collaboration mode introduced in `docs/specs/2026-05-15-codex-handoff-design.md` and the Codex wiki at `docs/codex-wiki/`.

## Problem

The BookLogic v0.4 mission (`docs/specs/2026-05-14-booklogic-v0.4-mission-design.md`) called for six PRs (D1 EDN boundary, D2 ingest-trace, D3 BookLogic core, D4 BookLogic full, D5 Bermuda migration + real Z3, D6 osmotic-pressure). PRs 1–3 have merged. PR-3 shipped the BookLogic compiler in the project template only; Bermuda still runs the pre-BookLogic v0.2 pipeline. D2 has an exporter but no consumer. D4, D5, D6 are entirely not started. Six Bermuda CLJS files (143 LOC) have zero tests and zero CI coverage. The `BookLogic CLJS integration` CI job that's green on `main` exercises a scaffolded fresh project, not the Bermuda code that actually runs in the smoke pipeline.

Mid-mission, a two-agent collaboration (Codex implements, Claude reviews) was introduced. That mode added a parallel phase-numbering scheme in `docs/codex-wiki/` that drifts from the mission spec's PR numbering, an extra phase ("PR-3.5 CLJS ingester port") that is not in the mission slate, and three layers of handoff briefs under `docs/handoffs/`. The work is going to be finished by Claude alone. The Codex scaffolding is dead weight.

## Goal

Finish v0.4 as a Claude-only effort across five PRs. Strip the two-agent scaffolding. Land the four remaining mission deliverables (D2 closeout, D4 full forms, D5 Bermuda migration + Z3 CI, D6 osmotic-pressure) plus a cleanup PR that picks up D1's loose ends and the CLJS test gap.

## Non-goals

- No new mission deliverables beyond what v0.4 already declared.
- No rewrite of the merged PR-1/2/3 work.
- No deletion of the mission spec body (the design is sound; only the Codex-handoff appendix goes).
- No backwards-compatibility shim for the Codex wiki — it's a meta-doc, not interface code.

## Approach

Five PRs in dependency order. Each PR is independently reviewable and revertible. The "one problem per PR" rule from `AGENTS.md` is preserved; coupling determines what bundles together.

```
PR-cleanup ──► PR-D2 ──► PR-4 ──► PR-5 ──► PR-6
   │             │         │        │        │
   │             │         │        │        └─ osmotic-pressure showcase (D6)
   │             │         │        └────────── Bermuda migration + real Z3 (D5)
   │             │         └─────────────────── BookLogic active forms (D4)
   │             └───────────────────────────── ingest-trace wired into verifier (D2 closeout)
   └─────────────────────────────────────────── strip Codex scaffolding; D1 data hygiene; CLJS test gap
```

PR-cleanup and PR-D2 are short (~3-4 days, ~2 days). PR-4 is the long pole (~2-3 weeks). PR-5 follows (~2 weeks). PR-6 is a showcase (~1.5 days). Total ~5-6 weeks.

## PR slate

### PR-cleanup — Strip Codex scaffolding, D1 hygiene, CLJS test gap

**Problem:** Two-agent scaffolding to delete. Two Bermuda data files still in JSON-stamped-as-EDN. Six CLJS files with no tests, no CI, and at least one suspected-buggy rule.

**Deletes:**
- `docs/codex-wiki/` (whole directory: 00-index, 01-audit-findings, 02-pr3.5-notes, 03-pr4-notes, 04-pr5-notes, 05-pr6-notes, 99-lessons)
- `docs/handoffs/2026-05-15-codex-*.md` (the four handoff briefs)
- `docs/specs/2026-05-15-codex-handoff-design.md`
- `openspec/changes/codex-phase-0/` (whole directory)

**Edits:**
- `AGENTS.md` — strip two-agent workflow language; replace with a one-paragraph "single-agent (Claude) workflow" note
- `docs/specs/2026-05-14-booklogic-v0.4-mission-design.md` — remove the Codex-handoff appendix if any; body stays
- Any plan file referencing "PR-3.5 CLJS ingester port" (the Codex-injected phase not in the mission slate)

**New work:**
- Convert `verifiers/bermuda/rules/seed.edn` and `verifiers/bermuda/rules/grounded.edn` from JSON syntax to real EDN with `Keyword` keys (D1 cleanup the original PR-1 missed)
- Create `verifiers/bermuda/cljs-orchestrator/test/` with `shadow-cljs` test target and `cljs.test` cases for each of the six in-tree files:
  - `bermuda.bridge` — stub native addon; assert call shapes
  - `bermuda.core` — CLI dispatch on `translate`/`verify`/`typeset`
  - `bermuda.ir` — malli round-trips for `Atom`, `Formula`, `Claim`, `Verdict`
  - `bermuda.nl-to-fol` — `claim->formula` with quantity-shaped and opaque inputs
  - `bermuda.phases` — pre/post contract violations raise
  - `bermuda.unify` — trivial sanity
- Fix any bug surfaced in `nl-to-fol/claim->formula` (audit flagged `~?pred` plus `:variable` shape as likely-broken against the `:keyword` constraint)
- New CI job: `cljs-bermuda-test` running `npx shadow-cljs compile test && node out/test.js` on `ubuntu-latest`

**Acceptance:**
- `grep -ri "codex" docs/` returns nothing in active documentation
- `grep -ri "two-agent" docs/` returns nothing
- `verifiers/bermuda/rules/seed.edn` round-trips through `read_edn_file` to the same Python value
- `cljs-bermuda-test` CI job green
- No regression in existing CI

### PR-D2 — Wire ingest-trace into the verifier

**Problem:** `export_symbolic_trace.py` emits `analysis/ingest-trace.edn` but no verifier consumes it. The Bermuda verifier reads `claims/ledger.jsonl` directly, bypassing the symbolic-event stream the spec called for.

**Edits:**
- `verifiers/bermuda/scripts/run_verification.py` — Phase 1 reads `<workspace>/analysis/ingest-trace.edn` if present, falls back to `ledger.jsonl` for legacy workspaces
- `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/phases.cljs` — extend `translate` to accept either claim-list shape (legacy) or trace-event shape (new)
- `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/nl_to_fol.cljs` — dispatch on event head: `(claim/verified ...)` produces a formula, `(source/ingested ...)` produces nothing, `(atom/emitted ...)` passes through

**New tests:**
- Python: `test_run_verification_consumes_trace.py` — synthesise a 3-event trace, assert the verifier loads it and emits the expected atoms
- CLJS: extend `bermuda.nl-to-fol` test to cover each event head; one negative case for unknown head

**Acceptance:**
- `run_verification.py` exits 0 against a fresh workspace that has `analysis/ingest-trace.edn` but no `claims/ledger.jsonl`
- Existing legacy-path tests still pass
- The Bermuda smoke pipeline in CI still passes

### PR-4 — BookLogic active forms (D4)

**Problem:** `booklogic.cljs.tmpl` implements `defsort`, `defpredicate`, `deflift`. The four active forms (`defrule`, `defconstraint`, `defquery`, `defremedy`) are absent. `axioms.rs` is a no-op stub; `kg.rs` is a 6-line `TODO: replace with cozo`. `book-qa.propose_writeback` has no BookLogic awareness.

**New work in `skills/neurosym-forge/assets/project-template/`:**
- Extend `cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl` with the four expanders. Each compiles its EDN form to the appropriate backend artifact.
- `defrule` → meander rewrite rule appended to `rules/rules.edn` (mostly identity transform from v0.2's existing rule shape; the wrapper is the value)
- `defconstraint` → entry in `rust-verifier/src/axioms.rs`. Codegen emits a Z3 `assert_and_track` call for each constraint with the tracker name derived from `:track`. Includes the `on-unsat` defect ticket shape for the verdict path.
- `defquery` → entry in `rust-verifier/src/kg.rs`. Replaces the stub with a real Cozo backend: each `defquery` compiles to a parameterised Cozo script invoked at verification time. Results become defect tickets.
- `defremedy` → entry in a new `rules/remedies.edn` consumed by `book-qa.scripts.propose_writeback.py`.

**New work in `skills/book-qa/scripts/propose_writeback.py`:**
- Accept BookLogic remedy proposals: each remedy carries `:when` pattern + `:propose` transition + `:requires`. The script matches verdict shape against `:when` and emits the proposed transition if matched. `:requires :human-review` means no auto-apply.

**Per-form tests (template-level):**
- `tests/test_booklogic_defrule.py` — compile a sample form; assert the rule lands in `rules/rules.edn`
- `tests/test_booklogic_defconstraint.py` — compile; assert `axioms.rs` contains the expected `assert_and_track` line; tracker map JSON shape correct
- `tests/test_booklogic_defquery.py` — compile; assert `kg.rs` contains the Cozo script and the dispatch entry
- `tests/test_booklogic_defremedy.py` — compile; assert `remedies.edn` entry; assert `propose_writeback` matches a fixture verdict to a remedy

**Cozo integration test:**
- `tests/test_kg_cozo_smoke.py` — declare one `defquery`, populate a fixture knowledge graph, assert query result shape
- New Rust dep: `cozo = { version = "0.7", default-features = false, features = ["compact"] }` already declared as optional; switch to active

**Acceptance:**
- All four forms have at least one TDD-shaped passing test
- `axioms.rs` generated from a sample project compiles under `cargo check`
- `kg.rs` Cozo path returns expected rows for one fixture query
- `propose_writeback` emits a remedy-driven transition for a fixture verdict
- Update mission spec § D4 footer to note the active forms landed in PR-4

**Internal split if needed:** if Cozo wiring is intricate, split into PR-4a (`defconstraint` + `axioms.rs` — pure Z3 path) and PR-4b (`defquery` + Cozo + `defremedy` + writeback — data path). Decision point: end of week 1.

### PR-5 — Bermuda migration + real Z3 (D5)

**Problem:** `verifiers/bermuda/rules/` still v0.2 hand-coded. `canonical.rs` still hand-edited. Four quantitative predicates missing. CI has no cargo build for the verifier. D13 never fires end-to-end.

**Edits:**
- Rewrite `verifiers/bermuda/rules/` as BookLogic source: `sorts.edn`, `predicates.edn`, `lifts.edn`, `rules.edn`, `constraints.edn`, `queries.edn`, `remedies.edn`
- Cover the existing five Bermuda predicates plus four new quantitative ones: `population`, `land-area-km2`, `gdp-usd-billion`, `hospital-beds-kemh`
- Delete `verifiers/bermuda/rust-verifier/src/canonical.rs`
- Check in generated `verifiers/bermuda/rust-verifier/src/axioms.rs` (regenerated by BookLogic compiler invocation in scaffold-or-update)
- `verifiers/bermuda/scripts/prose_patterns.py` becomes a thin wrapper that loads the regex table generated from `lifts.edn`
- Append four quantitative claims to `examples/bermuda-manual/claims/ledger.jsonl` (append-only contract preserved)

**CI:**
- New job `bermuda-z3-build` on `ubuntu-latest`: `cargo build --manifest-path verifiers/bermuda/rust-verifier/Cargo.toml --features z3`
- New job `bermuda-z3-verify`: builds, runs `npm run verify` against the Bermuda workspace, asserts D13 ticket fires for ch-02 parish-count drift
- `test_run_verification.py` drops `stub_verifier=True` default; the stub stays available for fast local iteration but real Z3 is the CI gate

**Acceptance:**
- BookLogic compiler invoked on Bermuda's `rules/` produces `axioms.rs` byte-identical to the version committed
- `cargo build` of the Bermuda verifier succeeds on `ubuntu-latest` CI
- Real Z3 run against Bermuda returns `:unsat` with ch-02 prose-claim id in the unsat core
- `book-qa` emits one D13 critical ticket against the ch-02 drift
- All 23 Bermuda Python tests still pass

### PR-6 — Osmotic-pressure showcase (D6)

**Problem:** v0.4 promises a non-book domain to prove BookLogic is reusable. None exists.

**New work:**
- Greenfield `verifiers/osmotic_pressure/`:
  - `rules/sorts.edn`, `predicates.edn`, `lifts.edn`, `constraints.edn` (the seven minimal BookLogic forms — no queries or remedies for the showcase)
  - `claims_clean.jsonl` — i=2, M=0.154, T=298.15, π=780202.5 → expect `:sat`
  - `claims_doctored.jsonl` — i=1, same M/T/π → expect `:unsat` with offending claim in core
  - Scaffold via `python -m scripts.scaffold_project --name "Osmotic pressure" --slug osmotic_pressure`
  - Generated `axioms.rs` includes the `~=` (approximate equality) constraint with 3% tolerance

**CI:**
- New job `osmotic-pressure-smoke`: scaffold + build + run both fixture ledgers; assert `:sat` and `:unsat` verdicts respectively

**Acceptance:**
- Scaffolded project builds with zero hand-edits
- Both fixture verdicts match expected
- Demonstrates `~=` codegen (the D4 implementation must support this; if not, PR-6 surfaces the gap and feeds back into PR-4)

## What stays from the existing repo

- The mission spec body (`docs/specs/2026-05-14-booklogic-v0.4-mission-design.md`) — design source of truth.
- The PR-1, PR-2, PR-3 plans — historical record of merged work; preserved unchanged.
- The audit findings doc (`docs/specs/2026-05-16-production-readiness-audit-findings.md`) — current-state snapshot.
- All seven core skill SKILL.md files and the eighth (`neurosym-forge`).
- The existing 628-test green gate from PR #38.

## What goes

- The Codex two-agent workflow design and its derivatives.
- The phase-numbering scheme that diverged from the mission spec.
- The "PR-3.5 CLJS ingester port" phase that was never in the mission slate.

## Risks

- **Z3 bundled build on Linux CI** — the mission spec flagged this as Open Question #5; PR-5 commits to `ubuntu-latest` as the canonical gate. Local Windows builds remain best-effort.
- **PR-4 scope** — `defconstraint`/`axioms.rs` + `defquery`/Cozo + `defremedy`/writeback may not fit one PR. Pre-declared internal split documented above; decision point end of week 1.
- **`nl_to_fol` latent bug** — PR-cleanup's test-first approach surfaces this. If the fix requires reshaping the IR schema, PR-cleanup grows; that's acceptable.
- **Bermuda data migration** — the four quantitative claims appended to `ledger.jsonl` need locator-text spans in real Bermuda sources. If the existing thesis-synthesised ledger can't carry them, PR-5 either (a) extends `synthesize_bermuda_ledger.py` to emit them or (b) adds them as `:status :proposed` rather than `:verified` and notes the gap.
- **Cozo Cargo build** — `cozo 0.7` with `compact` features has been declared but never built. If it fails on `ubuntu-latest`, PR-4 either fixes the build or makes Cozo optional via a feature flag.

## Open questions

1. **Should PR-4 ship the `~=` operator?** Mission spec § Open Question #1 says yes, codegen in PR-4. PR-6 osmotic-pressure depends on it. Confirmed: in scope for PR-4.
2. **Should `propose_writeback` auto-apply BookLogic remedies?** Mission spec says `:requires :human-review` blocks auto-apply. Default for remedies without `:requires` is auto-apply. PR-4 implements this default.
3. **Should the existing JSON-stamped `seed.edn`/`grounded.edn` migration happen in PR-cleanup or wait for PR-5?** PR-cleanup is the right home — the files are static data, not in the BookLogic source set; migrating them now eliminates the JSON-pretending-EDN risk in the v0.2 codepath that's still live.

## Deliverables

1. This design doc (committed in PR-cleanup).
2. Five TDD plans at `docs/plans/2026-05-17-booklogic-{cleanup,d2-wiring,pr4,pr5,pr6}.md`.
3. Five merged PRs.
4. Updated mission spec § footer noting the Claude-only finish.
5. Audit findings doc updated to reflect each closure as PRs land.

## Estimated total effort

~5-6 weeks across 5 PRs. Four review checkpoints between PRs.
