# Capability: kg-prose-eval (delta for live-eval-gate)

This change ADDS requirements REQ-EVAL-008…013 to the existing `kg-prose-eval`
capability. The landed S0 change reached REQ-EVAL-007; this delta continues that
sequence without renumbering any existing ID.

EARS classification is noted per requirement. Each requirement leads with its
subject and SHALL/SHALL NOT; the EARS trigger/condition is in the requirement
text and pinned by its scenarios.

## Definitions

- **live build** — a real chapter build produced by `book-compose`'s release flow
  (preflight → assemble → render → manifest), as opposed to the S0 frozen mini-task
  fixture; the build snapshot and its side products are the input this delta scores.
- **build report** — the per-chapter and aggregated artifact the live eval emits,
  covering the six metric families (attribution, factuality, reasoning, contradiction,
  rigor, fusion) for the build.
- **advisory vs. gating** — *advisory* means a metric is recorded and reported but
  does not fail the build; *gating* means a metric is a release-gate signal that can
  fail the build. The live eval is advisory by default.
- **baselined** — a metric has accumulated enough measured live builds to fix a
  threshold; only a baselined metric in the configured subset may become gating.

## ADDED Requirements

### Requirement: REQ-EVAL-008 — Live eval runs over a real build (Event-driven)

When a real chapter build completes, the live eval SHALL run the S0 harness over the
build's side products and prose, computing the six metric families on the live build.

Rationale: S0's metrics have only ever scored the frozen mini-task; the capstone is
the harness measuring an actual chapter build, which is what makes every v0.5 surface
finally observable on real prose.

#### Scenario: a completed build is scored by the S0 harness

- **WHEN** a real chapter build completes and the live eval runs over its snapshot
- **THEN** the S0 harness computes the six metric families (attribution, factuality, reasoning, contradiction, rigor, fusion) over the build's side products and drafted prose
- **AND** `skills/book-knowledge/tests/test_live_eval_gate.py::test_live_eval_runs_over_real_build` passes

### Requirement: REQ-EVAL-009 — Per-chapter and aggregated build report (Ubiquitous)

The live eval SHALL emit a build report that records each metric family per chapter
and aggregated across the build.

Rationale: a single aggregate hides per-chapter regressions; the report must carry
both granularities so a weak chapter is visible against the build total.

#### Scenario: the report carries per-chapter and aggregated metrics

- **WHEN** the live eval scores a build of more than one chapter
- **THEN** the build report contains, for each of the six metric families, a per-chapter value and a build-level aggregate
- **AND** `skills/book-knowledge/tests/test_live_eval_gate.py::test_build_report_per_chapter_and_aggregate` passes

### Requirement: REQ-EVAL-010 — Comparative metric records both arms (Optional)

Where a comparative metric is declared (claim-first vs. flat), the live eval SHALL
record both arms on the real build and SHALL report their delta.

Rationale: the decisive S0 experiment is the claim-first-vs-flat comparison; on the
live path it is only meaningful if both arms are measured and the delta is reported,
not asserted.

#### Scenario: the claim-first vs. flat delta is reported on the real build

- **WHEN** the live eval runs with the claim-first-vs-flat comparative metric declared
- **THEN** the build report records the metric for both the claim-first arm and the flat arm and reports the signed delta between them
- **AND** a build with no comparative metric declared reports no delta
- **AND** `skills/book-knowledge/tests/test_live_eval_gate.py::test_comparative_metric_reports_delta` passes

### Requirement: REQ-EVAL-011 — Absent gold reports unscored (State-driven)

While gold is absent for a live chapter, the live eval SHALL report the dependent
metric as `unscored` and SHALL NOT report it as a zero score.

Rationale: a false zero is indistinguishable from a real failure and poisons the
aggregate; the S0 honesty contract requires `unscored` when there is no gold to
measure against, and that contract must hold on the live path.

#### Scenario: a gold-less chapter yields unscored, not zero

- **WHEN** the live eval scores a chapter for which no gold exists for a metric
- **THEN** that metric is reported `unscored` for the chapter and is excluded from the aggregate rather than counted as zero
- **AND** a chapter with gold for that metric is scored normally
- **AND** `skills/book-knowledge/tests/test_live_eval_gate.py::test_absent_gold_reports_unscored` passes

### Requirement: REQ-EVAL-012 — Advisory by default, gating once baselined (Ubiquitous)

The live eval SHALL be advisory by default and SHALL treat a configured metric subset
as a release-gate signal only once that subset is baselined.

Rationale: gating before a threshold is baselined would stall every build on noise;
the default is advisory, and gating is an opt-in over a baselined subset.

#### Scenario: advisory by default, gating only on a baselined subset

- **WHEN** the live eval runs with no gating configured
- **THEN** every metric is advisory and the build does not fail on any metric
- **AND** **WHEN** a baselined metric subset is configured as gating and a metric in it breaches its threshold
- **THEN** the live eval fails the build on that metric
- **AND** `skills/book-knowledge/tests/test_live_eval_gate.py::test_advisory_default_and_gated_subset` passes

### Requirement: REQ-EVAL-013 — Read-only and deterministic (Ubiquitous)

The live eval SHALL read the build's side products read-only, leaving them
byte-identical, and SHALL be deterministic given the build snapshot and stubbed model
seams.

Rationale: an eval that mutates the build it scores, or whose result drifts across
runs, cannot be a trustworthy gate; the live eval observes and reproduces.

#### Scenario: scoring is read-only and reproducible

- **WHEN** the live eval scores the same build snapshot twice with the model seams stubbed
- **THEN** the build's side products are byte-identical before and after each run, and the two build reports are identical
- **AND** `skills/book-knowledge/tests/test_live_eval_gate.py::test_read_only_and_deterministic` passes
