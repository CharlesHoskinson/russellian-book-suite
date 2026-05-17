# Tasks: booklogic-d2-wiring

See `docs/plans/2026-05-17-booklogic-d2-wiring.md` for full TDD steps. Task numbers correspond 1:1.

## Phase 1 — Python trace-aware Phase-1 reader

- [ ] T1.1: Failing test for trace-only workspace; verifier loads N atoms. (REQ-TRACE-001)
- [ ] T1.2: Implement `run_verification.py` trace dispatch. (REQ-TRACE-001, REQ-TRACE-002)

## Phase 2 — Legacy fallback

- [ ] T2.1: Legacy-only workspace test passes. (REQ-TRACE-003)

## Phase 3 — CLJS event-aware translate

- [ ] T3.1: `shadow-cljs :test` already exists from cleanup; if not, add. (REQ-CLJS-ORCH-001)
- [ ] T3.2: `nl_to_fol` test cases for each event head. (REQ-CLJS-ORCH-010)
- [ ] T3.3: Implement `event->formula` dispatcher. (REQ-CLJS-ORCH-010, REQ-CLJS-ORCH-011)

## Phase 4 — Integration sweep

- [ ] T4.1: End-to-end test with synthesised trace. (REQ-TRACE-004)
- [ ] T4.2: Regression sweep — all Bermuda Python tests. (no REQ — meta)
- [ ] T4.3: Regression sweep — CLJS test suite. (no REQ — meta)
- [ ] T4.4: Confirm Bermuda smoke pipeline still green. (no REQ — meta)

## Phase 5 — Smoke + PR

- [ ] T5.1: Full sweep. (no REQ — meta)
- [ ] T5.2: Push + open PR. (no REQ — meta)
