# Change: booklogic-pr5-bermuda-migration

**Sprint:** 4 of 5
**Branch:** `feat/booklogic-pr5`
**GitHub Milestone:** `booklogic-pr5-bermuda-migration`

## Why

Bermuda still runs the pre-BookLogic v0.2 pipeline: `canonical.rs` is
hand-edited, `predicates.edn` is hand-written, the four quantitative
predicates promised by the mission (`population`, `land-area-km2`,
`gdp-usd-billion`, `hospital-beds-kemh`) are absent, there is no real
Z3 build in CI, and the ch-02 parish-count drift (ledger says 9, prose
says 8) does not fire a D13 ticket end-to-end. The headline mission
deliverable (D4: Bermuda migrated; D13 fires on real Z3) is unmet.

## What

- Rewrite `verifiers/bermuda/rules/` as BookLogic source: `sorts.edn`,
  `predicates.edn`, `lifts.edn`, `rules.edn`, `constraints.edn`,
  `queries.edn`, `remedies.edn`.
- Append the four quantitative claims to
  `examples/bermuda-manual/claims/ledger.jsonl`.
- Delete `canonical.rs`; check in generated `axioms.rs`.
- `prose_patterns.py` becomes a thin loader of the lift-generated regex table.
- Add `bermuda-z3-build` + `bermuda-z3-verify` CI jobs on `ubuntu-latest`.
- End-to-end smoke fires D13 against the ch-02 drift at
  `examples/bermuda-manual/book/releases/6.0.0/chapter-bundles/ch-02-v6/draft.md:44`.
- `test_run_verification.py` drops `stub_verifier=True` default.

## Capabilities touched

- `bermuda-rules` — ADD/MODIFY requirements for the BookLogic-sourced rules
- `verifier-build` — ADD requirement for real Z3 cargo build on `ubuntu-latest`
- `qa-defect-pipeline` — ADD requirement for end-to-end D13 fire on parish drift
- `cljs-orchestrator` — ADD requirement for `verify` subcommand on real verdicts

## Implementation notes

See `docs/plans/2026-05-17-booklogic-pr5.md` (9 phases, ~16 tasks).

## Acceptance

- BookLogic compiler on Bermuda's `rules/` produces `axioms.rs`
  byte-identical to the committed file
- `cargo build` of Bermuda verifier succeeds on `ubuntu-latest` CI
- Real Z3 run against Bermuda returns `:unsat` with ch-02 prose-claim id
  in the unsat core
- `book-qa` emits one D13 critical ticket against the ch-02 drift
- All 23 Bermuda Python tests still pass
- All REQ IDs added are test-covered
