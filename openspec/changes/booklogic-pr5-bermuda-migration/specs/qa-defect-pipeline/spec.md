# Capability delta: qa-defect-pipeline — change: booklogic-pr5-bermuda-migration

## ADD

### REQ-QA-PIPE-020 — Event-driven

When the Bermuda verifier returns `:unsat` against the v6.0.0 release artifacts
with the ch-02 prose drift at
`examples/bermuda-manual/book/releases/6.0.0/chapter-bundles/ch-02-v6/draft.md:44`,
the verdict's unsat core shall contain the prose-claim id corresponding to
"Richard Norwood divided the colony into eight parishes" plus the ledger
claim id `clm-2026-000008` (parishes=9).

**Rationale:** End-to-end D13 fire on the canonical drift.
**Tested by:** `verifiers/bermuda/tests/test_ch02_drift_e2e.py::test_unsat_core_carries_both_claims` (added in pr5 T6.2)

### REQ-QA-PIPE-021 — Ubiquitous

The book-qa end-to-end smoke suite shall include the ch-02 drift fixture as
one of its scenarios.

**Rationale:** Smoke regression for the headline mission deliverable.
**Tested by:** `verifiers/bermuda/tests/test_ch02_drift_e2e.py::test_drift_fixture_present` (added in pr5 T6.1)

### REQ-QA-PIPE-024 — Ubiquitous

The `.github/workflows/ci.yml` `bermuda-z3-verify` job shall execute the
ch-02 drift fixture on every PR.

**Rationale:** CI must gate the regression on every change.
**Tested by:** `.github/workflows/ci.yml` job `bermuda-z3-verify` step that invokes `pytest verifiers/bermuda/tests/test_ch02_drift_e2e.py` (added in pr5 T6.1)

### REQ-QA-PIPE-022 — Event-driven

When verifier-defects.json carries a `:verdict :unsat` for a build, book-qa
shall emit exactly one D13 ticket per claim id in the unsat core, with
`:severity :critical`.

**Rationale:** Each surfaced claim is one defect.
**Tested by:** `skills/book-qa/tests/test_lint_d13_from_verifier.py::test_unsat_core_to_d13_tickets` (added in pr5 T6.3)

### REQ-QA-PIPE-023 — State-driven

While `examples/bermuda-manual/qa-config.yaml` carries `enable_verification:
true`, the book-qa lint_artifact pass shall read `qa/verification-defects.json`
and incorporate D13 tickets into the defect summary.

**Rationale:** Verification defects are gated by workspace config.
**Tested by:** `test_lint_d13_from_verifier.py::test_config_gate` (added in pr5 T6.3)

## MODIFY

(none)

## REMOVE

(none)
