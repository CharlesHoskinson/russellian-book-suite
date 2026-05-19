# Capability delta: framework-eval — change: tier5-metta-onboarding-eval

## ADD

### REQ-EVAL-060 — Ubiquitous

The framework SHALL ship a fourth domain prompt at
`skills/neurosym-forge/eval/prompts/grandparent-metta.md` describing a
2-rule MeTTa-runtime verifier: `Parent` facts plus the rule
`(= (Grandparent $x $z) (, (Parent $x $y) (Parent $y $z)))`. The
prompt SHALL be one paragraph, SHALL NOT name `:backend :metta`
directly, AND SHALL reference SUPPORT_MATRIX consultation as a hint
that backend choice is part of the task.

**Rationale:** The onboarding bench measures whether the docs steer a
fresh agent to the right backend. Naming `:backend :metta` in the
prompt would short-circuit the measurement; omitting it makes the
prompt a real test of post-Tier-5 doc clarity on multi-hop reachability.
**Tested by:** `skills/neurosym-forge/eval/tests/test_grandparent_prompt.py::test_prompt_present_and_does_not_name_metta_backend` (added in T5.1).

### REQ-EVAL-061 — Ubiquitous

The onboarding-bench harness SHALL accept the grandparent-metta domain
alongside the existing three (toy-temperature, toy-species,
toy-claims-per-chapter). The per-run CSV schema SHALL include a
`metta_backend_used: bool` column derived post-run by checking whether
`rules/constraints.edn` contains at least one `:backend :metta` form.
The column placement SHALL be between `error_recovery_count` and
`asks_for_help_count`.

**Rationale:** The new column is the empirical signal of whether the
agent reached the new backend at all — independent of whether `make
ci` passed. Existing CSV consumers read by header name (per
REQ-EVAL-051) so the addition is non-breaking.
**Tested by:** `eval/tests/test_metta_backend_uptake_column.py::test_csv_header_includes_metta_backend_used` (added in T5.2).

### REQ-EVAL-062 — Ubiquitous

A SUCCESS outcome on the grandparent-metta prompt SHALL be defined as
all three of: (a) `make ci` PASSES, (b) the agent's
`rules/constraints.edn` contains at least one `:backend :metta` form,
AND (c) the verdict surface (`work/verification-defects.json` or
equivalent) includes a `:metta-results` key populated by Phase O's
runtime.

**Rationale:** A three-part SUCCESS definition pins the exact path the
docs should steer the agent down; weakening any one clause would
admit a passing run that did not actually exercise the new backend.
**Tested by:** `eval/tests/test_metta_backend_uptake_column.py::test_success_requires_all_three_conditions` (added in T5.2).

### REQ-EVAL-063 — Unwanted behaviour

IF the agent reaches `make ci PASS` on the grandparent-metta prompt
WITHOUT using `:backend :metta` (e.g., translates the multi-hop
relation to `:backend :z3` instead), the eval SHALL record the
terminal state `SUCCESS_WITHOUT_METTA`. This SHALL NOT count as a
hard failure of the eval — it is a flagged data point indicating that
the docs may underdescribe when `:metta` is the right tool.

**Rationale:** A pass that bypasses the new backend is meaningful
data, not a bug. Treating it as a hard failure would force the eval
to fail on a valid-but-suboptimal solution; recording it as a flagged
outcome surfaces the docs-clarity question to the maintainer who
reads the report.
**Tested by:** `eval/tests/test_metta_backend_uptake_column.py::test_pass_without_metta_records_success_without_metta` (added in T5.2).

### REQ-EVAL-064 — Optional feature

WHERE the eval run uses the `stub` backend (the deterministic test
path that mirrors REQ-EVAL-051's stub-mode for the existing prompts),
the eval SHALL produce the terminal state `STUB_SUCCESS`
deterministically, regardless of the constraints.edn content.

**Rationale:** Stub-backend runs exist to test the harness machinery
without measuring docs clarity. A separate terminal state keeps the
stub data out of the SUCCESS / SUCCESS_WITHOUT_METTA bookkeeping so
the aggregator's percentages stay honest.
**Tested by:** `eval/tests/test_metta_backend_uptake_column.py::test_stub_backend_produces_stub_success` (added in T3.2).

### REQ-EVAL-065 — Ubiquitous

The aggregator report `docs/eval/onboarding-bench-report.md` SHALL
grow a "MeTTa-backend-uptake" section reporting, for the
grandparent-metta prompt only: percent of runs that used
`:backend :metta` (SUCCESS), percent that bypassed to `:z3`
(SUCCESS_WITHOUT_METTA), percent that failed to reach `make ci`, and
percent that were stub-only (STUB_SUCCESS). The section SHALL include
the documented interpretation paragraph naming what a high
SUCCESS_WITHOUT_METTA rate implies for the docs.

**Rationale:** Numbers without interpretation are noise; the
interpretation paragraph turns the report into an actionable input
for the next docs-clarity iteration.
**Tested by:** `eval/tests/test_summary_report.py::test_report_has_metta_backend_uptake_section` (added in T4.2).
