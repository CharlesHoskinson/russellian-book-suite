# Capability delta: framework-eval — change: eval-onboarding-bench

## ADD

### REQ-EVAL-050 — Ubiquitous

The framework SHALL ship an onboarding benchmark harness at
`skills/neurosym-forge/eval/onboarding-bench.py` that scripts a
fresh-agent session per run: spin up an isolated workspace containing
only `skills/neurosym-forge/` and `docs/booklogic-dsl-reference.md`,
hand the agent a one-paragraph domain spec, capture every tool call
and stdout line, and measure time-to-each-milestone (`make extract`
PASS, `make ci` PASS).

**Rationale:** A fresh-agent harness is the only repeatable way to
verify "the docs are sufficient" without runner contamination. Human
re-runs leak knowledge between attempts; a fresh agent has no such
contamination, so the rates the bench reports reflect the docs'
clarity, not the operator's familiarity.
**Tested by:** `skills/neurosym-forge/eval/tests/test_harness_smoke.py::test_harness_runs_with_three_domains_and_emits_csv` (added in M1.4).

### REQ-EVAL-051 — Ubiquitous

The benchmark SHALL run against at least 3 distinct domain prompts
(drawn from `docs/booklogic-dsl-reference.md` §6 Cookbook or
comparable toy domains) and produce a CSV per run with columns:
`prompt_id`, `agent_id`, `run_id`, `started_at`, `ended_at`,
`extract_at_seconds`, `ci_at_seconds`, `tool_call_count`,
`greps_inside_skill`, `greps_outside_skill`, `error_recovery_count`,
`asks_for_help_count`, `terminal_state`.

**Rationale:** A single-domain bench measures one path; three domains
measure breadth. The CSV columns are the dimensions the
report-aggregator and CI-regression check consume — they are part of
the contract.
**Tested by:** `eval/tests/test_csv_schema.py::test_per_run_csv_has_required_columns` and `test_three_prompts_wired` (added in M3.1 / M4.1).

### REQ-EVAL-052 — Optional feature

WHERE the benchmark detects an agent reading or grepping a path
outside the isolated workspace or `skills/neurosym-forge/`, the
benchmark SHALL flag a documentation gap, record the offending path
in the per-run output, and continue the run.

**Rationale:** A read outside the doc bundle is the agent saying
"the bundle did not answer my question, I had to look at the source".
That path becomes a documentation gap. The bench captures the path
without aborting the run, so the agent's eventual outcome (reach the
milestone or not) is preserved as a signal about how recoverable the
gap was.
**Tested by:** `eval/tests/test_doc_gap_detector.py::test_outside_skill_read_is_flagged_but_not_fatal` (added in M2.1).

### REQ-EVAL-053 — Unwanted behaviour

IF the agent fails to reach `make extract` PASS within the configured
wall-time budget (default 30 minutes), THEN the benchmark SHALL
record a `TIMEOUT_extract` terminal state, capture the agent's final
attempted file state under the run output directory, and exit the
run without retrying.

**Rationale:** An open-ended bench will hang on a stuck agent and
make CI cost unbounded. The budget bounds the wall-time per run; the
captured final state preserves the agent's last attempt so the
post-mortem can show how close it came. No retry: each run is a clean
data point.
**Tested by:** `eval/tests/test_timeout_handling.py::test_thirty_minute_budget_records_timeout_and_captures_state` (added in M1.4).

### REQ-EVAL-054 — Ubiquitous

The benchmark SHALL emit a summary report at
`docs/eval/2026-05-XX-onboarding-bench-report.md` after each
all-domain run, aggregating: percent of domains that reached
`make extract` PASS, percent that reached `make ci` PASS, the top 5
documentation gaps surfaced (paths most frequently grepped outside
the skill), and the top 5 framework gaps surfaced (clusters of
repeated error-recovery patterns).

**Rationale:** The CSV is the raw data; the report is the readable
synthesis. Top-5 doc gaps and top-5 framework gaps are the two
actionable inputs to the next iteration of docs / framework — they
directly drive what Tier 5+ work targets.
**Tested by:** `eval/tests/test_summary_report.py::test_report_has_milestone_rates_and_two_top_five_tables` (added in M4.2).

### REQ-EVAL-055 — Ubiquitous

The benchmark SHALL be re-runnable in CI on a weekly schedule to
track regression. The CI workflow SHALL compare each milestone-reach
rate against the prior week's baseline persisted under
`eval/baselines/`. IF any milestone-reach rate drops below 80% of the
baseline value, THEN the workflow SHALL fail with a message naming
the domain, the milestone, the prior rate, and the new rate.

**Rationale:** A single-run number tells us today's docs-quality; a
trend tells us whether changes are improving or eroding it. The 80%
gate is loose enough to absorb agent-side variance and tight enough
to catch a real documentation regression. The named-failure message
is the diff a maintainer reads to decide between fix vs accept.
**Tested by:** `eval/tests/test_regression_gate.py::test_workflow_fails_with_named_regression_below_80pct` (added in M5.2).
