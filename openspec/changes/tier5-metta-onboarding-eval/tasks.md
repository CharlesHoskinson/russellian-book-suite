# Tasks: tier5-metta-onboarding-eval

See `docs/plans/2026-05-19-tier5-metta-runtime.md` Phase T for full TDD
steps. Task numbers correspond 1:1.

## Phase T.1 — Prompt + harness wiring

- [ ] T1.1: Author `skills/neurosym-forge/eval/prompts/grandparent-metta.md` per design.md (one paragraph; does not name `:backend :metta`). (REQ-EVAL-060)
- [ ] T1.2: Register the prompt in the bench's domain registry; add `--domain grandparent-metta` as a valid value. (REQ-EVAL-061)

## Phase T.2 — CSV schema

- [ ] T2.1: Extend the CSV header with `metta_backend_used` between `error_recovery_count` and `asks_for_help_count`. (REQ-EVAL-061)
- [ ] T2.2: Implement `metta_backend_used(workspace)` post-run check that greps `rules/constraints.edn` for `:backend :metta`. (REQ-EVAL-061)

## Phase T.3 — SUCCESS taxonomy

- [ ] T3.1: Implement the SUCCESS / SUCCESS_WITHOUT_METTA distinction in the terminal-state classifier. (REQ-EVAL-062, REQ-EVAL-063)
- [ ] T3.2: Implement the STUB_SUCCESS deterministic-path output for stub-backend runs. (REQ-EVAL-064)

## Phase T.4 — Aggregator report

- [ ] T4.1: Extend `docs/eval/onboarding-bench-report.md` template with a "MeTTa-backend-uptake" section per design.md. (REQ-EVAL-065)
- [ ] T4.2: Wire the aggregator to count SUCCESS vs SUCCESS_WITHOUT_METTA vs failed for the grandparent-metta prompt only. (REQ-EVAL-065)

## Phase T.5 — Tests + commit

- [ ] T5.1: Add `eval/tests/test_grandparent_prompt.py` asserting the prompt file exists and contains the documented constraints (mentions `Parent`, `Grandparent`, "multi-hop"). (REQ-EVAL-060)
- [ ] T5.2: Add `eval/tests/test_metta_backend_uptake_column.py` asserting the CSV header and the post-run detection logic. (REQ-EVAL-061, REQ-EVAL-062, REQ-EVAL-063)
- [ ] T5.3: Commit `openspec(tier5): metta onboarding eval change folder (REQ-EVAL-060..065)` once specs land; commit subsequent implementation commits per task group.
