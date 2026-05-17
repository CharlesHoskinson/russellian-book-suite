# Tasks: booklogic-cleanup

This file is the executor's checklist. Each task line cites the REQ IDs it
satisfies in parentheses. Source bodies, full commands, and TDD steps live
in the implementation-notes plan at
`docs/plans/2026-05-17-booklogic-cleanup.md` — task numbers in that plan
correspond 1:1 with task numbers here.

## Phase 1 — Strip Codex scaffolding

- [ ] T1.1: Create branch `feat/booklogic-cleanup`.
- [ ] T1.2: Delete `docs/codex-wiki/`. (no REQ)
- [ ] T1.3: Delete `docs/handoffs/2026-05-15-codex-*.md`. (no REQ)
- [ ] T1.4: Delete `docs/specs/2026-05-15-codex-handoff-design.md`. (no REQ)
- [ ] T1.5: Delete `openspec/changes/codex-phase-0/`. (no REQ; superseded by Phase 0 of the EARS migration)
- [ ] T1.6: Edit `AGENTS.md` — drop the minimal two-agent language. (no REQ)
- [ ] T1.7: Strip PR-3.5 references from `docs/specs/2026-05-14-booklogic-v0.4-pr3-design.md`. (no REQ)
- [ ] T1.8: Run grep gate; assert no `codex` matches in active docs. (no REQ)

## Phase 2 — D1 data hygiene

- [ ] T2.1: Write failing test asserting real-EDN round-trip on `seed.edn` and `grounded.edn`. (REQ-EDN-010, REQ-EDN-011)
- [ ] T2.2: Convert `verifiers/bermuda/rules/seed.edn` to real EDN. (REQ-EDN-010, REQ-BERMUDA-RULES-001)
- [ ] T2.3: Convert `verifiers/bermuda/rules/grounded.edn` to real EDN. (REQ-EDN-011, REQ-BERMUDA-RULES-002)

## Phase 3 — CLJS test harness

- [ ] T3.1: Add `shadow-cljs :test` node-test target. (REQ-CLJS-ORCH-001)
- [ ] T3.2: Tests for `bermuda.unify`. (REQ-CLJS-ORCH-002)
- [ ] T3.3: Tests for `bermuda.ir` (malli round-trips). (REQ-CLJS-ORCH-003)
- [ ] T3.4: Tests for `bermuda.nl-to-fol` (rule shape; the failing case for the bug). (REQ-CLJS-ORCH-004)
- [ ] T3.5: Tests for `bermuda.phases` (pre/post contract violations). (REQ-CLJS-ORCH-005)
- [ ] T3.6: Tests for `bermuda.bridge` (stub addon; call shapes). (REQ-CLJS-ORCH-006)
- [ ] T3.7: Tests for `bermuda.core` (CLI dispatch). (REQ-CLJS-ORCH-007)

## Phase 4 — Fix `nl_to_fol` bug

- [ ] T4.1: Fix the schema collision in `claim->formula`; reuse the failing test from T3.4. (REQ-CLJS-ORCH-008)

## Phase 5 — CI integration

- [ ] T5.1: Add `cljs-bermuda-test` job to `.github/workflows/ci.yml`. (REQ-CLJS-ORCH-009)

## Phase 6 — Smoke + PR

- [ ] T6.1: Full sweep; scaffold a fresh project to confirm nothing regressed. (no REQ — meta)
- [ ] T6.2: Push branch, open PR with body referencing this change directory. (no REQ — meta)
