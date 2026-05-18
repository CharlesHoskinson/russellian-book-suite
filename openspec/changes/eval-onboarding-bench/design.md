# Design: eval-onboarding-bench

## Why automate

The third-verifier eval is one human path. The onboarding bench is the
automated, repeatable, regression-tracking complement. Together they answer
the framework-usefulness question along both axes a fresh user might
travel: a deliberate single-domain author (third-verifier), and a generic
agent steered only by the docs (onboarding-bench).

## Bench architecture

```
+--------------------------------------------------------------+
|                    onboarding-bench.py                        |
+--------------------------------------------------------------+
|                                                              |
|   ┌──────────────────────────────────────────────────────┐   |
|   │ Per run, for each domain prompt:                     │   |
|   │                                                      │   |
|   │   1. spin up an isolated workspace                   │   |
|   │      (tempdir; clean copy of skill + docs only)      │   |
|   │   2. hand agent the doc bundle + one-paragraph spec  │   |
|   │   3. start a fresh Claude/Codex session              │   |
|   │   4. capture stdout, stderr, tool calls (jsonl)      │   |
|   │   5. measure milestones                              │   |
|   │      - first `make extract` PASS                     │   |
|   │      - first `make ci` PASS                          │   |
|   │   6. on timeout (30min), record TIMEOUT_<milestone>  │   |
|   │   7. flag any read/grep that escapes                 │   |
|   │      skills/neurosym-forge/ — that's a doc gap       │   |
|   │   8. emit one row to runs.csv                        │   |
|   └──────────────────────────────────────────────────────┘   |
|                                                              |
|   At end of all-domain run:                                  |
|     - aggregate into report.md                               |
|     - top-5 documentation gaps                               |
|     - top-5 framework gaps                                   |
|     - milestone-reach rates per domain                       |
+--------------------------------------------------------------+
```

## Run isolation

Each run lives in `eval/runs/<utc-timestamp>-<domain>/`:

```
eval/runs/2026-05-18T14-30-00-toy-temperature/
├── workspace/              # isolated copy of skill + docs
├── domain-spec.md          # the one-paragraph prompt the agent saw
├── agent-transcript.jsonl  # every tool call, every stdout line
├── milestones.json         # { extract_at_seconds, ci_at_seconds, ... }
└── run.csv                 # one-row CSV (joins with weekly aggregate)
```

The workspace is a clean copy of `skills/neurosym-forge/` plus
`docs/booklogic-dsl-reference.md`. Nothing else. The agent has no access
to `verifiers/osmotic_pressure/` or `verifiers/bermuda/` — that would
contaminate the eval with the existing worked examples.

## Doc-gap detection

The bench monitors agent tool calls. If the agent reads or greps any
file outside `skills/neurosym-forge/` or `docs/booklogic-dsl-reference.md`
(or its isolated workspace), the bench flags that path as a "doc-gap
escape". The interpretation: the agent expected an answer in the doc
bundle, did not find it, and resorted to the source. That path is a
documentation gap.

The flag is non-fatal — the agent is allowed to continue — but the gap
is recorded for the weekly report.

## Milestones + failure modes

Two milestones to reach:

1. **`make extract` PASS.** Indicates the agent has authored a coherent
   `lifts.edn` and got the ingester to extract at least one ground atom.
   This is the first observable signal that the agent has internalised
   the regex-dialect contract, the subject-naming convention, and the
   value-kind alignment.
2. **`make ci` PASS.** Indicates the agent has authored a constraint
   set, produced a fixture, and got the full pipeline through Z3 with
   a verdict.

Failure modes captured:

- `TIMEOUT_extract` — 30 min wall time elapsed, `make extract` never green.
- `TIMEOUT_ci` — extract green, `make ci` never green within budget.
- `EXIT_NONZERO` — agent ended its session without reaching either milestone.
- `INFINITE_LOOP` — same tool call ≥10 times consecutively.
- `ASKS_FOR_HELP` — agent emits a clarifying question to stdout (counted,
  not fatal — but each instance is a doc gap).

The 30-minute budget is configurable per run; 30 min is the default because
the third-verifier eval (REQ-EVAL-040..047) implicitly targets that as the
upper-bound a human onboarding would tolerate.

## Domain prompts

At least three distinct domains. Initial set (drawn from cookbook §6 of
the DSL reference):

1. **Temperature-bounded reaction** — `lo < x < hi -> P(x)`. Tests
   inequality encoding + implication.
2. **String-typed entity match** — single-predicate Latin-name match.
   Tests `:string` value-kind path.
3. **Count-by-aggregation toy** — claims-per-chapter via `defquery`.
   Tests the Cozo-only path (which is `wired-builder` per
   SUPPORT_MATRIX.md — a deliberate hard case).

Each prompt is one paragraph: domain in plain English + the kind of defect
the verifier should catch. The agent translates that prose into the DSL.

## CSV schema

Per-run CSV row:

```csv
prompt_id,agent_id,run_id,started_at,ended_at,extract_at_seconds,ci_at_seconds,
tool_call_count,greps_inside_skill,greps_outside_skill,error_recovery_count,
asks_for_help_count,terminal_state
```

`terminal_state` ∈ `{extract_only, ci_pass, timeout_extract, timeout_ci,
exit_nonzero, infinite_loop}`.

## Aggregation + regression

After all-domain runs complete:

1. Compute per-domain milestone-reach rates (% of agents that reached
   each milestone within budget).
2. Top-5 doc gaps: paths most frequently grepped outside the skill.
3. Top-5 framework gaps: clusters of `error_recovery_count` (same error
   pattern hit by multiple agents).
4. Emit `docs/eval/2026-05-XX-onboarding-bench-report.md`.

For weekly CI: persist prior week's rates in `eval/baselines/`. The CI
workflow runs the bench, compares against the baseline, and fails if any
milestone-reach rate drops below 80% of the baseline. The named regression
is the disease — fixing it (or accepting the drop) is the response.

## Why fresh-agent (not human-replay)

A human running the eval twice contaminates the second run with the first
run's learnings. A fresh agent's state has no such contamination because
each run is a clean session with no prior knowledge of the docs or the
domain beyond the prompt. The bench therefore produces a noise floor
that reflects the docs' clarity, not the eval-runner's familiarity.

## Why three milestones not one

`make extract` PASS without `make ci` PASS is a real intermediate state:
the agent has learned the lift conventions but not the constraint
conventions. Reporting both rates separately distinguishes "regex-dialect
docs sufficient" from "constraint-encoder docs sufficient" — they are
independent failure axes and aggregating them would hide the signal.
