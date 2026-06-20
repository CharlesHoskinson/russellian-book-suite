# Tasks: booklogic-v0.5-boolean-quantifiers

Plan: `docs/plans/2026-05-18-booklogic-v0.5-extended-operators.md`

Phase / task numbers correspond 1:1 with plan sections.

> **Reconciled 2026-06-16.** The implementation landed via PR #134; this file's
> checkboxes were never updated. Verified on `origin/main` @ `c695de9`:
> `test_codegen_axioms.py` + `test_codegen_axioms_quantifiers.py` = 51 passing,
> incl. `test_generate_and_assertion`/`test_generate_or_assertion`; encoder arms
> and `extended_operators_v0_5.edn` present. Boxes below reflect that reality. Two
> items are **carried to `booklogic-v0.6-predicate-uf-semantics`** (the
> structural-only quantifier encoding shipped here is sound only after v0.6).

## Phase A — OpenSpec record

- [x] Task 0: OpenSpec record + branch readiness (this file)

## Phase B — Boolean connectives

- [x] REQ-SMT-046 (`and`) — Task 1: Bool-subexpression encoder + `and` / `or`
- [x] REQ-SMT-047 (`or`) — Task 1: Bool-subexpression encoder + `and` / `or`
- [x] REQ-SMT-050 (Bool-subexpression helper) — Task 1: `_emit_bool_subexpr` extraction
- [x] REQ-SMT-048 (`not`) — Task 2: `not` and `=>`
- [x] REQ-SMT-049 (`=>`) — Task 2: `not` and `=>`

## Phase C — Variable refs + general quantifiers

- [x] REQ-SMT-053 (bound-variable refs) — Task 3: Bound-variable resolution
- [x] REQ-SMT-051 (`forall`) — Task 4: `forall` and `exists` (structural; sound after v0.6)
- [x] REQ-SMT-052 (`exists`) — Task 4: `forall` and `exists` (structural; sound after v0.6)
- [x] REQ-SMT-054 (sort-registry check) — Task 4: undeclared-sort validation in `generate_axioms_source`

## Phase D — Docs sync + golden fixture

- [x] REQ-BOOKLOGIC-051 (SUPPORT_MATRIX) — Task 5: rows present (quantifier row carries the v0.5 caveat; promoted to wired in v0.6 REQ-BOOKLOGIC-054)
- [ ] REQ-BOOKLOGIC-052 (DSL ref §2.6, §2.7) — **NOT DONE; carried to v0.6 REQ-BOOKLOGIC-055.** §2.6/§2.7 were already `defquery`/`defremedy`; the operator docs were never added under valid section numbers.
- [x] REQ-BOOKLOGIC-053 (golden fixture) — `tests/golden/extended_operators_v0_5.edn` present

## Phase E — End-to-end

- [ ] REQ-SMT-055 (cargo check + deterministic output) — **carried to v0.6 REQ-SMT-061** (byte-identical pin for the nil-arity shipped verifiers is formalized there)

## Phase F — PR

- [x] Task 7: Push + open PR — landed via PR #134
