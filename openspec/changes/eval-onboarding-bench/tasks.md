# Tasks: eval-onboarding-bench

## Phase N.1 — Prompts + harness

- [x] N1.1: Author three domain prompts under
  `skills/neurosym-forge/eval/prompts/`. (REQ-EVAL-050)
- [x] N1.2: Write `skills/neurosym-forge/eval/onboarding-bench.py`
  with the doc-bundle assembler, `run_agent` with `stub`/`claude-code`/
  `codex` backends, CSV writer, and regression gate. (REQ-EVAL-050,
  REQ-EVAL-051, REQ-EVAL-053)

## Phase N.2 — Doc-gap detection

- [x] N2.1: Add `detect_doc_gaps` helper that scans an agent log
  directory and returns paths grepped outside the doc bundle. Stub
  backend produces `[]`. (REQ-EVAL-052)

## Phase N.3 — Timeout

- [x] N3.1: Wire `--timeout-seconds` (default 1800) into the harness
  and document the `TimeoutExpired -> outcome = "TIMEOUT_extract"`
  contract. (REQ-EVAL-053)

## Phase N.4 — Aggregator + report

- [x] N4.1: Write `skills/neurosym-forge/eval/aggregate_runs.py` that
  reads CSVs and emits `docs/eval/onboarding-bench-report.md`.
  (REQ-EVAL-054)

## Phase N.5 — Weekly CI

- [x] N5.1: Add `.github/workflows/onboarding-bench.yml` running on a
  Monday 06:00 UTC cron + workflow_dispatch. (REQ-EVAL-055)

## Phase N.6 — Tests

- [x] N6.1: Add `tests/test_onboarding_bench.py` covering prompt count
  and stub-run success.
