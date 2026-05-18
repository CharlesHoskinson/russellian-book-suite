# Change: eval-onboarding-bench

**Track:** Usefulness verification (2 of 2)
**Branch:** `eval/onboarding-bench`
**Depends on:** Tier 1 docs landed (tier1-references-docs in particular —
the doc bundle the bench hands the fresh agent IS the new references/ content).
Sibling to `eval-third-verifier`.

## Why

Tier 1 plugged the dead-end references referenced by `SKILL.md` and shipped
`docs/booklogic-dsl-reference.md` + `SUPPORT_MATRIX.md`. The acceptance criterion
for that work was "files exist, contain the documented sections, pass
existence-and-headings checks". That is the wrong test. The right test is
"a fresh LLM agent handed only those files can produce a working verifier".

The third-verifier eval (`eval-third-verifier`) answers that question along
a single human-graded path. It is necessary but not sufficient: a single
human is one data point, the eval is non-repeatable, and once a person has
read the docs once their second attempt is contaminated. The onboarding
bench gives the framework an automated, repeatable, regression-tracking
answer to the same question.

A fresh agent is spawned with:

- `skills/neurosym-forge/SKILL.md`
- `docs/booklogic-dsl-reference.md`
- The six `references/` docs that Tier 1 landed
- A one-paragraph domain spec (drawn from `docs/booklogic-dsl-reference.md`
  §6 Cookbook or a comparable toy domain)
- An isolated workspace, no internet, no pre-existing verifier code

The agent's task is to scaffold a verifier and reach `make extract` PASS,
then `make ci` PASS. Every tool call, every grep into source outside the
skill folder, every error-recovery attempt is logged. The bench produces
a per-run CSV and a weekly aggregated report.

## What

- Implement `skills/neurosym-forge/eval/onboarding-bench.py` — a harness that
  spawns a fresh agent session, hands it the doc bundle and a domain spec,
  captures tool calls, and measures time-to-milestones.
- Wire the bench against ≥3 distinct domain prompts.
- Emit a per-run CSV and a summary report at
  `docs/eval/2026-05-XX-onboarding-bench-report.md`.
- Add a weekly CI job that reruns the bench and fails on regression
  (milestone-reach-rate drop below 80%).

## Capabilities touched

- `framework-eval` — MODIFY (extends the shared capability added by
  eval-third-verifier with REQ-EVAL-050..055; OpenSpec allows multiple
  parallel changes to ADD entries to the same capability spec file in
  separate change deltas)

## Implementation notes

See `docs/plans/2026-05-18-tier234-and-usefulness.md`, Phase M.

## Acceptance

- `skills/neurosym-forge/eval/onboarding-bench.py --domain <name>` produces
  a CSV with the documented columns and exits non-zero only on bench failure.
- ≥3 domain prompts wired.
- Summary report exists with documentation-gap and framework-gap top-5 lists.
- CI weekly workflow runs the bench and fails on regression-below-80%.
