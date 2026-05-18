# Change: eval-onboarding-bench

**Branch:** `feat/eval-onboarding-bench`
**Depends on:** none (independent eval harness)

## Why

The Tier-1 onboarding work makes claims about how quickly a fresh
author or fresh LLM agent can reach a working verifier given only the
neurosym-forge doc bundle. Today no automated signal disproves
documentation drift: SKILL.md, SUPPORT_MATRIX.md, and
`docs/booklogic-dsl-reference.md` are graded by hand. When a future PR
silently breaks the docs (renames a keyword, drops a form family,
removes an example), nothing fails until the next human onboarding
attempt. A weekly automated eval that drives a controlled "fresh
agent" attempt against a fixed set of domain prompts converts
onboarding regressions into CI signal.

## What

- Ship `skills/neurosym-forge/eval/onboarding-bench.py` — a harness
  that runs three domain prompts against a configurable agent backend
  (stub for CI, real LLM subprocess for production runs), captures
  milestone timings (extract-passed, ci-passed), and writes a CSV per
  run.
- Ship three domain prompts in
  `skills/neurosym-forge/eval/prompts/` covering distinct verifier
  shapes: numeric-bounds, aggregation/equality, string-shape.
- Ship `skills/neurosym-forge/eval/aggregate_runs.py` — reads all
  CSVs and emits `docs/eval/onboarding-bench-report.md` with
  reach-extract / reach-ci percentages and top doc / framework gaps.
- Ship `.github/workflows/onboarding-bench.yml` — a weekly cron + a
  regression gate that fails when the ci-reach rate drops below 80%
  for real-backend runs (stub runs are always green by construction).

## Capabilities touched

- `framework-eval` — ADD (new capability)

## Implementation notes

The stub backend is the load-bearing primitive: it lets the harness
run in CI without depending on an LLM runtime, so the workflow shape
itself is exercised on every weekly schedule. Real-backend wiring
(claude-code subprocess, codex subprocess) is left as a TODO inside
`run_agent` and is intentionally NOT plumbed in this change.

## Acceptance

- Three prompt files exist under
  `skills/neurosym-forge/eval/prompts/` and are picked up by the
  harness.
- `onboarding-bench.py --backend stub` produces a CSV and returns 0.
- `aggregate_runs.py` produces `docs/eval/onboarding-bench-report.md`
  from at least one CSV.
- A pytest sanity suite asserts both prompt count and stub-run
  success.
- A weekly GitHub Actions workflow runs the harness + aggregator and
  uploads the report as an artifact.
