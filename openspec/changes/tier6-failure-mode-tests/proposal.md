# Change: tier6-failure-mode-tests

**Tier:** 6 of 7 (theory-induction tier)
**Branch:** `plan/tier6-theory-induction`
**Depends on:** Tier 6 phases V (induction-grammar), W
(candidate-generation), X (smt-numeric-fitting)

## Why

Both deep-research reports surveyed the LLM-symbolic-loop
failure-mode literature and converged on the same top four
patterns that an induction layer must defend against:

- **False-Correction Loop** — LLM "fixes" a valid candidate
  in response to a spurious error message.
- **Outcome-Driven Constraint Violation** — LLM emits a
  trivially-true predicate (`(or true X)`) that covers every
  atom but says nothing.
- **Proof-Level Confabulation** — LLM emits a
  circular-reference rule that references its own defect id.
- **Memorization-vs-Induction** — Candidate passes on the
  training corpus but fails on the document-held-out fold,
  indicating the LLM memorised support rather than induced
  structure.

Phases V/W/X each implement a mitigation. This change ships
the regression tests that confirm those mitigations are
wired and that they fire on the canonical failure-mode
inputs.

## What

- A new test file
  `skills/neurosym-forge/tests/test_failure_modes.py`
  containing one test per failure-mode pattern (four tests
  total).
- A fixture directory
  `skills/neurosym-forge/tests/fixtures/failure_modes/`
  carrying the canonical broken candidates each test asserts
  against.
- A wall-clock budget (≤5 seconds per test) using stub
  providers so the suite stays cost-zero and CI-friendly.

## Capabilities touched

- `framework-eval` — EXTEND (adds REQ-TEST-040..045 on top
  of the existing REQ-EVAL / REQ-CORPUS regression base)

## Implementation notes

See `docs/plans/2026-05-19-tier6-theory-induction.md`,
Phase BB.

## Acceptance

- 6 REQ-TEST IDs (040-045) ship in
  `specs/framework-eval/spec.md`.
- Each of the four failure-mode tests asserts the framework
  rejects (or refuses to mutate on) the canonical broken
  input, naming the rejection reason.
- The suite runs in under 5 seconds per test under
  `pytest --durations=10` with the stub LLM provider.
- The four tests are visible in `pytest -k failure_mode`
  output.
