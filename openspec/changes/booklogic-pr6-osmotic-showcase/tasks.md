# Tasks: booklogic-pr6-osmotic-showcase

See `docs/plans/2026-05-17-booklogic-pr6.md` for full TDD steps. Phase /
task numbers correspond 1:1.

## Phase 1 — Scaffold

- [ ] T1.1: Run `scaffold_project --name "Osmotic pressure" --slug osmotic_pressure`. (REQ-OSMOTIC-001)

## Phase 2 — BookLogic source

- [ ] T2.1: `rules/sorts.edn` — `:solution`. (REQ-OSMOTIC-010)
- [ ] T2.2: `rules/predicates.edn` — four predicates. (REQ-OSMOTIC-011)
- [ ] T2.3: `rules/lifts.edn` — at least one lift. (REQ-OSMOTIC-012)
- [ ] T2.4: `rules/constraints.edn` — van 't Hoff with `~=` 3% tolerance. (REQ-OSMOTIC-013)

## Phase 3 — Fixture ledgers

- [ ] T3.1: `claims_clean.jsonl`. (REQ-OSMOTIC-020)
- [ ] T3.2: `claims_doctored.jsonl`. (REQ-OSMOTIC-021)

## Phase 4 — Codegen + build

- [ ] T4.1: Compile BookLogic to `axioms.rs`. (REQ-OSMOTIC-030)
- [ ] T4.2: `cargo build --features z3,bundled` (Linux canonical). (REQ-OSMOTIC-031)

## Phase 5 — End-to-end smoke

- [ ] T5.1: Clean ledger → `:sat`. (REQ-OSMOTIC-040)
- [ ] T5.2: Doctored ledger → `:unsat` with i=1 claim id in core. (REQ-OSMOTIC-041)

## Phase 6 — CI

- [ ] T6.1: Add `osmotic-pressure-smoke` job. (REQ-OSMOTIC-050)

## Phase 7 — Mission spec footer

- [ ] T7.1: Update mission spec § D5 with merge-SHA placeholder. (no REQ — meta)

## Phase 8 — PR + v0.4.0 Release

- [ ] T8.1: Push, open PR. (no REQ — meta)
- [ ] T8.2: On merge, publish v0.4.0 GitHub Release. (no REQ — meta)
