# Tasks: tier2-encoder-extensions

See `docs/plans/2026-05-18-tier234-and-usefulness.md` Phase E.2 for full
TDD steps. Task numbers correspond 1:1.

## Phase E.2.1 — Comparison operators

- [ ] E2.1.1: Add failing test `skills/neurosym-forge/scripts/tests/test_codegen_axioms_operators.py::test_lt_le_emit_real_lt_le`. (REQ-SMT-040)
- [ ] E2.1.2: Extend `_emit_z3_block` dispatch with `<` → `Real::lt` / `Int::lt`, `<=` → `Real::le` / `Int::le`. (REQ-SMT-040)
- [ ] E2.1.3: Add failing test `test_gt_ge_emit_real_gt_ge`. (REQ-SMT-041)
- [ ] E2.1.4: Extend dispatch with `>` and `>=`. (REQ-SMT-041)

## Phase E.2.2 — Division and conditional

- [ ] E2.2.1: Add failing test `test_div_emits_real_div_for_real_operands`. (REQ-SMT-042)
- [ ] E2.2.2: Extend dispatch with `/`. (REQ-SMT-042)
- [ ] E2.2.3: Add failing test `test_ite_emits_typed_branch`. (REQ-SMT-043)
- [ ] E2.2.4: Extend dispatch with `ite` (ternary, branch-type inference). (REQ-SMT-043)

## Phase E.2.3 — Unknown-head failure surface

- [ ] E2.3.1: Add failing test `test_unknown_head_error_enumerates_supported_set`. (REQ-SMT-044)
- [ ] E2.3.2: Introduce `_SUPPORTED_ASSERT_HEADS` tuple and reference it in the codegen error message. (REQ-SMT-044)

## Phase E.2.4 — End-to-end constraint smoke

- [ ] E2.4.1: Add a temperature-window worked example to `verifiers/osmotic_pressure/tests/fixtures/` and assert codegen + cargo check succeed.

## Phase E.2.5 — DSL reference doc

- [ ] E2.5.1: Update `docs/booklogic-dsl-reference.md` § 2.5 to enumerate the full operator set with worked snippets per operator. (REQ-SMT-045)
- [ ] E2.5.2: Commit `openspec(tier2): encoder extensions change folder (REQ-SMT-040..045)` once specs land.
