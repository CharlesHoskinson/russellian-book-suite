# Tasks: tier5-framing-reckoning

See `docs/plans/2026-05-19-tier5-metta-runtime.md` Phase S for full TDD
steps. Task numbers correspond 1:1.

## Phase S.1 — Concepts doc

- [ ] S1.1: Write `docs/concepts/metta-runtime-grounded-vs-shaped.md` (~150 lines, structure per design.md). (REQ-BOOKLOGIC-060)

## Phase S.2 — SKILL.md update

- [ ] S2.1: Retire the pre-Tier-5 sentence in `skills/neurosym-forge/SKILL.md` that implies the framework "runs MeTTa" without qualifier; replace with the design.md "after" copy. (REQ-BOOKLOGIC-061)
- [ ] S2.2: Add the hyperon-experimental crate version + alpha callout near the top of SKILL.md. (REQ-BOOKLOGIC-061)
- [ ] S2.3: Link `docs/concepts/metta-runtime-grounded-vs-shaped.md` from SKILL.md. (REQ-BOOKLOGIC-061)

## Phase S.3 — SUPPORT_MATRIX.md

- [ ] S3.1: Add the `defconstraint :backend :metta | wired (alpha) | hyperon-experimental` row. (REQ-BOOKLOGIC-062)
- [ ] S3.2: Add a `wired (alpha)` legend entry to the status-legend section. (REQ-BOOKLOGIC-062)

## Phase S.4 — references/metta-idioms.md rewrite

- [ ] S4.1: Lift §1 "What we borrow" subsections to acknowledge they describe the EDN encoding (not a runtime). (REQ-BOOKLOGIC-063)
- [ ] S4.2: Add §3 "What we now embed at runtime" listing Phase O / P / Q / R capabilities. (REQ-BOOKLOGIC-063)
- [ ] S4.3: Add the retraction block listing any pre-Tier-5 sentence that overstated the integration. (REQ-BOOKLOGIC-063)

## Phase S.5 — Drift lint

- [ ] S5.1: Extend `skills/neurosym-forge/tests/test_support_matrix.py` with `test_metta_row_not_described_as_production_or_stable`. (REQ-BOOKLOGIC-064)
- [ ] S5.2: Add the same assertion shape against SKILL.md and references/metta-idioms.md `:metta`-adjacent sections. (REQ-BOOKLOGIC-064)

## Phase S.6 — Deprecation runbook + DSL reference

- [ ] S6.1: Write `docs/operations/deprecate-metta-backend.md` per the design.md outline. (REQ-BOOKLOGIC-065)
- [ ] S6.2: Add the `:metta` row to `docs/booklogic-dsl-reference.md` §2.5 backend table with the `(alpha)` qualifier. (REQ-BOOKLOGIC-066)
- [ ] S6.3: Commit `openspec(tier5): framing reckoning change folder (REQ-BOOKLOGIC-060..066)` once specs land; commit subsequent implementation commits per task group.
