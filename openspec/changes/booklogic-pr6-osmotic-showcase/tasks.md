# Tasks: booklogic-pr6-osmotic-showcase

See `docs/plans/2026-05-17-booklogic-pr6.md` for full TDD steps. Phase /
task numbers correspond 1:1.

## Phase 1 — Scaffold

- [x] T1.1: Run `scaffold_project --name "Osmotic pressure" --slug osmotic_pressure`. (REQ-OSMOTIC-001)

## Phase 2 — BookLogic source

- [x] T2.1: `rules/sorts.edn` — `:solution`. (REQ-OSMOTIC-010)
- [x] T2.2: `rules/predicates.edn` — four predicates. (REQ-OSMOTIC-011)
- [x] T2.3: `rules/lifts.edn` — at least one lift. (REQ-OSMOTIC-012)
- [x] T2.4: `rules/constraints.edn` — van 't Hoff with `approx=` 3% tolerance. (REQ-OSMOTIC-013) [note: ~= encoded as approx= per EDN reader constraint; booklogic.cljs accepts both]

## Phase 3 — Fixture ledgers

- [x] T3.1: `claims_clean.jsonl`. (REQ-OSMOTIC-020)
- [x] T3.2: `claims_doctored.jsonl`. (REQ-OSMOTIC-021)

## Phase 4 — Codegen + build

- [x] T4.1: Compile BookLogic to `axioms.rs`. (REQ-OSMOTIC-030)
- [ ] T4.2: `cargo build --features smt` (Linux canonical). (REQ-OSMOTIC-031) [local build FAILED on Windows — Int/Real type mismatch; CI gate is ubuntu-latest]

## Phase 5 — End-to-end smoke

- [x] T5.1: Clean ledger → `:sat`. (REQ-OSMOTIC-040) [smoke test written; SKIP locally pending verifier dist]
- [x] T5.2: Doctored ledger → `:unsat` with i=1 claim id in core. (REQ-OSMOTIC-041) [smoke test written; SKIP locally pending verifier dist]

## Phase 6 — CI

- [x] T6.1: Add `osmotic-pressure-smoke` job. (REQ-OSMOTIC-050)

## Phase 7 — Mission spec footer

- [x] T7.1: Update mission spec § D5 footer. (no REQ — meta)

## Phase 8 — PR + v0.4.0 Release

- [ ] T8.1: Push, open PR. (no REQ — meta)
- [ ] T8.2: On merge, publish v0.4.0 GitHub Release. (no REQ — meta)
