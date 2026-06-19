# Capability: kg-prose-eval (delta for kg-prose-eval-harness)

This change ADDS the `kg-prose-eval` capability. All requirements below are new.

EARS classification is noted per requirement. Each requirement leads with its
subject and SHALL/SHALL NOT; the EARS trigger/condition is in the requirement
text and pinned by its scenarios.

## Definitions

- **frozen task** — a benchmark task whose ledger snapshot, chapter contract, and
  gold side-products are committed and never mutated in place; a new revision is a
  new task id.
- **side product** — a graph-structured output of a writing run other than prose:
  selected claims, cited spans, contradiction alerts, argument-acceptability
  warnings, proof-obligation traces, code↔claim links.
- **result-set equal** — equal as an unordered multiset of rows after a canonical
  sort (reused from `homoiconic-kg`).
- **gold** — human-verified reference data: verified source-spans per sentence,
  warning labels, link labels.

## ADDED Requirements

### Requirement: REQ-EVAL-001 — Frozen benchmark task (Ubiquitous)

The harness SHALL define a benchmark task as a committed bundle of a ledger
snapshot, a chapter contract, and gold side-products, stored under
`docs/eval/kg-prose/<task-id>/`, and SHALL treat each task as immutable once
committed.

Rationale: a moving benchmark cannot grade a sequence of sprints; immutability is
what makes a cross-sprint delta meaningful.

#### Scenario: a task bundles snapshot, contract, and gold

- **WHEN** a benchmark task directory is loaded
- **THEN** it contains a ledger snapshot, a chapter contract, and at least one gold side-product file
- **AND** `tests/test_eval_corpus.py::test_task_bundle_complete` passes

#### Scenario: a frozen task is not mutated in place

- **WHEN** the harness runs against a committed task
- **THEN** the task's snapshot and gold files are byte-identical before and after the run
- **AND** `tests/test_eval_corpus.py::test_task_immutable` passes

### Requirement: REQ-EVAL-002 — Metric families (Ubiquitous)

The metrics module SHALL compute the six metric families — attribution,
factuality, reasoning, contradiction, rigor, and fusion — each reported both
micro-averaged by sentence and macro-averaged by chapter where the family admits
both.

Rationale: the brief specifies internal, ledger-aligned metrics stricter than the
generic ALCE/FActScore references because the KG already stores exact spans.

#### Scenario: each family yields a score over a scored task

- **WHEN** the metrics module runs on a task with full gold
- **THEN** it returns a score for each of the six families, with micro and macro variants where defined
- **AND** `tests/test_eval_metrics.py::test_all_families_scored` passes

#### Scenario: factuality partitions atomic facts

- **WHEN** the factuality metric runs on a drafted chapter
- **THEN** every atomic fact is partitioned into exactly one of {verified-claim-backed, disputed-claim-backed, no-claim-binding, span-check-failed}
- **AND** the partitions sum to the atomic-fact count
- **AND** `tests/test_eval_metrics.py::test_factuality_partition_total` passes

### Requirement: REQ-EVAL-003 — Side products emitted alongside prose (Event-driven)

When the harness runs a writing task, the system SHALL emit the graph-structured
side products to a fixed schema in addition to the prose, so metrics read
structure rather than re-parsing text.

Rationale: measuring only prose forfeits the graph's advantage; the side-product
schema is the contract every later sprint writes to.

#### Scenario: a run emits structured side products

- **WHEN** the harness executes a task
- **THEN** it writes selected-claims, cited-spans, contradiction-alerts, warnings, proof-traces, and code-links to the declared side-product schema
- **AND** `tests/test_eval_harness.py::test_run_emits_side_products` passes

### Requirement: REQ-EVAL-004 — Goldens with result-set equality (Ubiquitous)

The harness SHALL compare every metric over every frozen task to a committed
golden and SHALL require result-set equality under canonical ordering.

#### Scenario: metric matches its golden

- **WHEN** a metric runs on a frozen task
- **THEN** its output is result-set-equal to the committed golden after canonical sort
- **AND** `tests/test_eval_goldens.py::test_metric_matches_golden` passes

### Requirement: REQ-EVAL-005 — Comparative metric records both arms (Optional)

Where a sprint declares a comparative metric, the harness SHALL record both the
treatment and the control arm and SHALL report their delta rather than a single
absolute.

Rationale: the brief's experiments (claim-first vs. flat bundle; link vs.
no-link) are deltas; reporting only the treatment hides the control.

#### Scenario: a comparative metric reports a delta

- **WHEN** a sprint registers a comparative metric with a treatment and a control arm
- **THEN** the harness runs both and reports the delta plus each arm's raw score
- **AND** `tests/test_eval_metrics.py::test_comparative_reports_both_arms` passes

### Requirement: REQ-EVAL-006 — Missing gold yields `unscored` (State-driven)

While gold data is absent for a task, the harness SHALL report the dependent
metric as `unscored` and SHALL NOT report a zero or a default score.

Rationale: a false zero is indistinguishable from a real failure and would poison
cross-sprint deltas.

#### Scenario: absent gold spans do not score as zero

- **WHEN** a task has no gold spans for attribution
- **THEN** the attribution metric returns `unscored` for that task
- **AND** `tests/test_eval_metrics.py::test_missing_gold_is_unscored` passes

### Requirement: REQ-EVAL-007 — Determinism guard (Unwanted)

If a metric run produces different output across two invocations on the same
snapshot with the same stubbed inputs, then the harness SHALL fail loudly and name
the non-deterministic metric.

Rationale: a non-deterministic grader cannot support result-set-equality goldens.

#### Scenario: non-determinism is caught

- **WHEN** a metric is invoked twice on one snapshot with identical stubbed inputs and the outputs differ
- **THEN** the harness raises with the offending metric named
- **AND** `tests/test_eval_harness.py::test_determinism_guard` passes
