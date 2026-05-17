# Tasks: booklogic-pr5-bermuda-migration

See `docs/plans/2026-05-17-booklogic-pr5.md` for full TDD steps. Phase /
task numbers correspond 1:1.

## Phase 1 — Author Bermuda BookLogic source

- [ ] T1.1: `rules/sorts.edn`. (REQ-BERMUDA-RULES-010)
- [ ] T1.2: `rules/predicates.edn` (5 existing + 4 new). (REQ-BERMUDA-RULES-011, REQ-BERMUDA-RULES-012)
- [ ] T1.3: `rules/lifts.edn` (every regex from `prose_patterns.py`). (REQ-BERMUDA-RULES-013)
- [ ] T1.4: `rules/rules.edn`. (REQ-BERMUDA-RULES-014)
- [ ] T1.5: `rules/constraints.edn` (5 existing facts + 4 new). (REQ-BERMUDA-RULES-015, REQ-BERMUDA-RULES-016)
- [ ] T1.6: `rules/queries.edn` (at least one Cozo query). (REQ-BERMUDA-RULES-017)
- [ ] T1.7: `rules/remedies.edn` (at least one remedy). (REQ-BERMUDA-RULES-018)

## Phase 2 — Codegen + lockstep

- [ ] T2.1: Compile BookLogic, generate `axioms.rs`. (REQ-VERIFIER-BUILD-030)
- [ ] T2.2: `test_axioms_lockstep.py` — codegen output stable. (REQ-VERIFIER-BUILD-031)
- [ ] T2.3: Delete `canonical.rs`. (REQ-BERMUDA-RULES-019)
- [ ] T2.4: Rewrite `prose_patterns.py` as a thin loader of the lift-generated table. (REQ-BERMUDA-RULES-020)

## Phase 3 — Quantitative claims in ledger

- [ ] T3.1: Append 4 quantitative claims to `examples/bermuda-manual/claims/ledger.jsonl`. (REQ-BERMUDA-RULES-021)

## Phase 4 — Local Z3 build (best-effort)

- [ ] T4.1: `cargo build --features z3,bundled` locally; capture diagnostics if it fails. (no REQ — meta)

## Phase 5 — CI Z3 build

- [ ] T5.1: Add `bermuda-z3-build` job. (REQ-VERIFIER-BUILD-040)
- [ ] T5.2: Add `bermuda-z3-verify` job. (REQ-VERIFIER-BUILD-041, REQ-QA-PIPE-020)

## Phase 6 — End-to-end D13 smoke

- [ ] T6.1: Author ch-02 drift fixture. (REQ-QA-PIPE-021)
- [ ] T6.2: Run full verifier; assert `:unsat` with claim id in core. (REQ-QA-PIPE-022)
- [ ] T6.3: Assert `book-qa` emits D13 critical ticket. (REQ-QA-PIPE-023)

## Phase 7 — `test_run_verification.py` migration

- [ ] T7.1: Drop `stub_verifier=True` default; CI uses real Z3. (REQ-VERIFIER-BUILD-042)

## Phase 8 — Mission spec footer

- [ ] T8.1: Update mission spec § D4 with merge-SHA placeholder. (no REQ — meta)

## Phase 9 — PR

- [ ] T9.1: Push + open PR. (no REQ — meta)
