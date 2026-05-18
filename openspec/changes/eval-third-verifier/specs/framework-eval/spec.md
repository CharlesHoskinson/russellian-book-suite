# Capability delta: framework-eval — change: eval-third-verifier

## ADD

### REQ-EVAL-040 — Ubiquitous

The framework SHALL ship a third domain verifier under
`verifiers/<chosen-domain>/` (initial target: `verifiers/epidemiology/`)
following the standard project structure: `rules/booklogic/`,
`fixtures/`, `rust-verifier/`, `cljs-orchestrator/`, `scripts/`,
`tests/`, `Makefile`, `package.json`, `pyproject.toml`, `deps.edn`,
`nbb.edn`, `shadow-cljs.edn`, `README.md`, `SKILL.md`.

**Rationale:** The two existing verifiers (`bermuda`, `osmotic_pressure`)
share their author with the framework. A third verifier on an
independent domain is the minimum bar for the "general-purpose"
framing being supported by evidence rather than assertion.
**Tested by:** `tests/test_third_verifier_layout.py::test_standard_project_files_present` (added in L1.1).

### REQ-EVAL-041 — Ubiquitous

The third verifier SHALL pass `make ci` end-to-end with at least 3
clean fixtures (no defects expected) and 2 doctored fixtures (one
false-positive trap exercising threshold-inequality, one
cross-document inconsistency exercising same-subject value drift).

**Rationale:** `make ci` green with mixed clean/doctored fixtures is
the working definition of "verifier production-ready" — it's the bar
the bermuda and osmotic_pressure verifiers meet. The third verifier
inherits the same bar so the eval is apples-to-apples.
**Tested by:** `tests/test_third_verifier_fixtures.py::test_make_ci_green_on_three_clean_two_doctored` (added in L3.5).

### REQ-EVAL-042 — Ubiquitous

The verifier author SHALL maintain a build log at
`docs/eval/2026-05-XX-third-verifier-build-log.md` recording every
roadblock encountered during the build, every workaround applied,
and every framework gap discovered. Each entry SHALL include the
symptom observed, the root cause identified, and the resolution
status (`fixed`, `workaround`, `deferred-to-tier-N`).

**Rationale:** The log is the evaluation artefact, not just the
verifier. A working verifier alone does not tell us whether the
framework is general-purpose or merely sufficient-for-one-extra-domain.
The log distinguishes "needed no workaround" from "ten workarounds, all
on the same axis" — which is the real signal.
**Tested by:** `tests/test_build_log_present.py::test_build_log_has_entries_with_required_fields` (added in L2.1).

### REQ-EVAL-043 — Unwanted behaviour

IF the verifier author encounters a roadblock and resolves it via a
workaround rather than a framework patch, THEN the workaround SHALL be
filed as a follow-up issue (or linked to an existing OpenSpec change)
naming the roadmap tier expected to close it — for instance, "Tier 2
encoder does not support `>=` natively, worked around with
`(not (< a b))`; tracked at <issue/change link>".

**Rationale:** Workarounds without follow-ups become invisible technical
debt. The build log forces every workaround into the open and binds it
to a planned change, so the framework's roadmap tier ordering can be
sanity-checked against the gaps the third domain actually surfaced.
**Tested by:** `tests/test_build_log_workarounds.py::test_every_workaround_links_a_tier_or_issue` (added in L4.2).

### REQ-EVAL-044 — Ubiquitous

The verifier SHALL surface at least one defect for each doctored
fixture: the threshold-violation fixture produces a verdict containing
a defect tied to the inequality constraint; the cross-document-drift
fixture produces a verdict containing a defect tied to the consistency
constraint. No false negatives.

**Rationale:** A doctored fixture that passes silently is the worst
failure mode of a verifier — it claims confidence where it has none.
The doctored fixtures are calibrated against the constraint set: each
one must surface as `:unsat` with a recognisable defect message.
**Tested by:** `tests/test_third_verifier_fixtures.py::test_doctored_fixtures_produce_defects` (added in L3.4).

### REQ-EVAL-045 — Ubiquitous

The verifier SHALL NOT surface any defect on any clean fixture: each
of the three clean fixtures produces a verdict with no defect entries.
No false positives.

**Rationale:** A verifier that fires on clean inputs is unusable — it
trains the reader to ignore its output. The clean fixtures bound the
verifier's precision: they SHALL pass without modification of the
constraint set.
**Tested by:** `tests/test_third_verifier_fixtures.py::test_clean_fixtures_produce_no_defects` (added in L3.4).

### REQ-EVAL-046 — Optional feature

WHERE the build surfaces a gap addressed by a planned Tier 2-4 change
(for instance: the absence of native `>=` encoding closed by a future
Tier 2 enhancement, or cross-claim aggregation closed by
tier3-cozo-runtime), the author SHALL document the gap in the build log
and link the OpenSpec change folder that closes it.

**Rationale:** This binds the eval output back into the roadmap. If
the third verifier surfaces gaps already on the roadmap, that
validates the roadmap's tier ordering; if it surfaces gaps not on the
roadmap, the eval has generated new planning input.
**Tested by:** `tests/test_build_log_workarounds.py::test_tier_links_resolve_to_change_folders` (added in L4.2).

### REQ-EVAL-047 — Ubiquitous

A final usefulness report at
`docs/eval/2026-05-XX-framework-usefulness-report.md` SHALL synthesise
the build log into three buckets: (1) features that worked first-try
from documentation alone, (2) features that required a workaround, with
the workaround linked to a planned change, and (3) capabilities the
verifier ended up not using because no acceptable workaround existed.
Each bucket SHALL be non-empty or explicitly noted empty.

**Rationale:** The build log is too granular for outside readers; the
usefulness report is the human-facing answer to "is the framework
general-purpose?" backed by concrete bucket counts. It is the
public-facing artefact of the eval.
**Tested by:** `tests/test_usefulness_report.py::test_three_buckets_present_and_classified` (added in L4.1).
