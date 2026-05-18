# Capability delta: framework-eval — change: eval-onboarding-bench

## ADD

### REQ-EVAL-050 — Ubiquitous

The framework SHALL ship an automated onboarding benchmark harness at
`skills/neurosym-forge/eval/onboarding-bench.py` that runs a
"fresh-agent attempts to scaffold a verifier given only the doc
bundle" eval against a fixed set of domain prompts.

**Rationale:** Documentation drift is silent today; weekly automation
converts it into CI signal.
**Tested by:** `tests/test_onboarding_bench.py::test_three_prompts_exist`

### REQ-EVAL-051 — Ubiquitous

The harness SHALL support multiple agent backends via a `--backend`
flag, including at minimum `stub` (deterministic in-process simulator
for CI) and placeholders for `claude-code` and `codex` subprocess
backends.

**Rationale:** The harness must exercise the CI pathway without an
LLM runtime dependency.
**Tested by:** `tests/test_onboarding_bench.py::test_stub_run_succeeds`

### REQ-EVAL-052 — Ubiquitous

The harness SHALL expose a `detect_doc_gaps(agent_log_dir)` helper
that returns paths the agent grepped outside the canonical doc bundle
(`SKILL.md`, `SUPPORT_MATRIX.md`, `references/**`, and
`docs/booklogic-dsl-reference.md`). For the stub backend the helper
returns an empty list.

**Rationale:** Doc-gap detection drives the aggregator's "top 5 doc
gaps" view, which directs future doc work.

### REQ-EVAL-053 — Unwanted behaviour

IF an agent invocation exceeds `--timeout-seconds` (default 1800),
THEN the harness SHALL record the outcome as `TIMEOUT_extract` (or
`TIMEOUT_ci` once that phase is reached) and continue with the next
prompt.

**Rationale:** A hung agent must not block the weekly report from
covering all prompts.

### REQ-EVAL-054 — Ubiquitous

The framework SHALL ship `skills/neurosym-forge/eval/aggregate_runs.py`
which reads every CSV produced by the harness and writes
`docs/eval/onboarding-bench-report.md` containing the reach-extract
percentage, reach-ci percentage, top five doc gaps, and top five
framework gaps.

**Rationale:** A weekly human-readable view is the only sustainable
way to drive the iteration loop.

### REQ-EVAL-055 — Unwanted behaviour

WHEN the harness runs against a non-stub backend AND the ci-reach
rate falls below 80%, the harness SHALL exit non-zero so that the
weekly CI workflow fails. Stub-backend runs SHALL always pass the
gate.

**Rationale:** The regression gate is the actual safety net; the
stub exemption keeps CI signal even before a real backend is wired.
