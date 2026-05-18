# Tasks: eval-onboarding-bench

See `docs/plans/2026-05-18-tier234-and-usefulness.md` Phase M for full
TDD steps. Task numbers correspond 1:1.

## Phase M.1 — Harness skeleton

- [ ] M1.1: Create `skills/neurosym-forge/eval/onboarding-bench.py` with CLI: `--domain <id>`, `--budget-seconds 1800`, `--out eval/runs/`. (REQ-EVAL-050)
- [ ] M1.2: Implement isolated-workspace setup: copy `skills/neurosym-forge/` + `docs/booklogic-dsl-reference.md` into a fresh tempdir per run; no other paths visible. (REQ-EVAL-050, REQ-EVAL-052)
- [ ] M1.3: Implement agent-spawn shim: start a fresh Claude/Codex session in the workspace, capture stdout + stderr + tool-call jsonl. (REQ-EVAL-050)
- [ ] M1.4: Implement milestone watcher: tail run logs for `make extract` PASS, `make ci` PASS; record `extract_at_seconds`, `ci_at_seconds`. (REQ-EVAL-050, REQ-EVAL-053)

## Phase M.2 — Doc-gap + framework-gap detection

- [ ] M2.1: Tool-call hook: flag any read/grep that escapes the workspace (paths outside `skills/neurosym-forge/` or the workspace root). Record the offending path. (REQ-EVAL-052)
- [ ] M2.2: Error-recovery counter: detect repeated failure-then-retry tool patterns; cluster by error message. (REQ-EVAL-051)
- [ ] M2.3: Asks-for-help counter: detect agent clarifying questions in stdout (heuristic: question-mark, "I need to know", "can you tell me"). (REQ-EVAL-052)

## Phase M.3 — Domain prompts

- [ ] M3.1: Author `skills/neurosym-forge/eval/prompts/toy-temperature.md` — temperature-bounded reaction. (REQ-EVAL-051)
- [ ] M3.2: Author `skills/neurosym-forge/eval/prompts/toy-species.md` — string-typed entity match. (REQ-EVAL-051)
- [ ] M3.3: Author `skills/neurosym-forge/eval/prompts/toy-claims-per-chapter.md` — count-by-aggregation. (REQ-EVAL-051)

## Phase M.4 — CSV + summary report

- [ ] M4.1: Emit per-run `run.csv` with the schema in design.md (prompt_id, agent_id, run_id, timestamps, milestones, counters, terminal_state). (REQ-EVAL-051)
- [ ] M4.2: Implement aggregator: produce `docs/eval/2026-05-18-onboarding-bench-report.md` with milestone-reach rates per domain, top-5 doc gaps, top-5 framework gaps. (REQ-EVAL-054)

## Phase M.5 — Weekly CI

- [ ] M5.1: Add `.github/workflows/onboarding-bench.yml` — schedule weekly, run the bench against the three default domains, persist results. (REQ-EVAL-055)
- [ ] M5.2: Add baseline-comparison step: read `eval/baselines/last-week.csv`, fail if any milestone-reach-rate drops below 80% of baseline; name the regression in the failure message. (REQ-EVAL-055)
- [ ] M5.3: Commit `openspec(eval): onboarding benchmark change folder (REQ-EVAL-050..055)` once specs land.

## Phase M.6 — Push + PR

- [ ] M6.1: Push branch `eval/onboarding-bench` and open PR.
- [ ] M6.2: Land once green CI and the first weekly bench produces a clean baseline.
