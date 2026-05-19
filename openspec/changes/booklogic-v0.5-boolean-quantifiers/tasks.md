# Tasks: booklogic-v0.5-boolean-quantifiers

Plan: `docs/plans/2026-05-18-booklogic-v0.5-extended-operators.md`

Phase / task numbers correspond 1:1 with plan sections.

## Phase A — OpenSpec record

- [x] Task 0: OpenSpec record + branch readiness (this file)

## Phase B — Boolean connectives

- [ ] REQ-SMT-046 (`and`) — Task 1: Bool-subexpression encoder + `and` / `or`
- [ ] REQ-SMT-047 (`or`) — Task 1: Bool-subexpression encoder + `and` / `or`
- [ ] REQ-SMT-050 (Bool-subexpression helper) — Task 1: `_emit_bool_subexpr` extraction
- [ ] REQ-SMT-048 (`not`) — Task 2: `not` and `=>`
- [ ] REQ-SMT-049 (`=>`) — Task 2: `not` and `=>`

## Phase C — Variable refs + general quantifiers

- [ ] REQ-SMT-053 (bound-variable refs) — Task 3: Bound-variable resolution
- [ ] REQ-SMT-051 (`forall`) — Task 4: `forall` and `exists`
- [ ] REQ-SMT-052 (`exists`) — Task 4: `forall` and `exists`
- [ ] REQ-SMT-054 (sort-registry check) — Task 4: undeclared-sort validation in `generate_axioms_source`

## Phase D — Docs sync + golden fixture

- [ ] REQ-BOOKLOGIC-051 (SUPPORT_MATRIX) — Task 5: SUPPORT_MATRIX + DSL ref + golden fixture (step 1)
- [ ] REQ-BOOKLOGIC-052 (DSL ref §2.6, §2.7) — Task 5: SUPPORT_MATRIX + DSL ref + golden fixture (steps 2–3)
- [ ] REQ-BOOKLOGIC-053 (golden fixture) — Task 5: SUPPORT_MATRIX + DSL ref + golden fixture (steps 4–5)

## Phase E — End-to-end

- [ ] REQ-SMT-055 (cargo check + deterministic output) — Task 6: Smoke-test on osmotic / bermuda + EpochPoET unblock

## Phase F — PR

- [ ] Task 7: Push + open PR (no REQ — controller-orchestrated)
