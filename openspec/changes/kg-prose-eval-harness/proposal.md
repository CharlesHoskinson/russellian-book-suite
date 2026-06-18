# Change: kg-prose-eval-harness

**Sprint:** S0 of the v0.5 KG-for-prose mission
**Branch:** `plan/kg-prose-roadmap` (roadmap); execution branch `feat/kg-prose-eval-harness`
**Capability:** `kg-prose-eval` (new)
**Roadmap:** `docs/specs/2026-06-17-kg-prose-enhancement-roadmap-design.md`
**Depends on:** the landed `homoiconic-kg` capability (Cozo seam + EDN compiler). No upstream sprint.

## Why

The v0.5 mission turns the knowledge graph into a writer-facing reasoning surface across nine sprints (S1–S9). None of those gains is measurable without a frozen benchmark. The repo's own discipline — "characterization first, goldens second, exact result-set equality wherever determinism allows" (REQ-KG-005) — says the harness comes before the features it grades.

The brief's decisive experiment is *claim-first graph bundles vs. flat passage bundles on the suite's own chapter-writing tasks*, not an abstract "GraphRAG vs RAG" claim. That experiment needs a benchmark whose inputs are ledger snapshots and whose outputs are graph-structured side products (selected claims, cited spans, contradiction alerts, proof traces), not only prose. S0 builds exactly that, so S1–S8 each land against a stable, shared measurement instead of inventing their own.

## What

1. A frozen benchmark corpus: a small set of chapter-writing tasks, each pinned to a committed ledger snapshot (raw claims, source-spans, thesis, chapter contract) under `docs/eval/kg-prose/`.
2. A metrics module computing, per task and aggregated (micro by sentence, macro by chapter):
   - **Attribution:** sentence-level citation precision/recall vs. human-verified spans; partial-support rate.
   - **Factuality (internal FActScore):** % of atomic facts backed by verified claims / by disputed claims / with no claim binding / whose cited spans pass the support check.
   - **Reasoning:** precision/recall of argument-acceptability warnings (`undefended-attack`, `unsupported-load-bearing`, `axiom-only-support`) vs. a small annotated gold set; chapter-level argument-closure %.
   - **Contradiction:** symbolic catch-rate, residual recall, false-positive rate (tracked separately).
   - **Rigor:** proof-obligation discharge rate, failed-obligation detection rate, gated-sentence-escape rate; unit-check pass rate; statistical-claim completeness rate.
   - **Fusion:** deterministic code↔claim link precision/recall vs. a hand-labeled sample.
3. A golden-result harness: each metric over each frozen task has a committed golden; the metric run is result-set-equal to its golden under canonical ordering.
4. A negative-control hook: every comparative metric (e.g. S1's claim-first vs. flat bundle, S6's link vs. no-link) records both arms so later sprints assert a delta, not an absolute.

Metrics consume only data the graph already produces (claims, spans, status, edges) plus the per-sprint side products S1–S8 emit; the harness defines the schema for those side products so sprints write to a fixed shape.

## Scope

- This change ships the corpus format, the metrics module, the golden harness, and stubs for the per-sprint side-product schemas (filled in as each sprint lands).
- It does **not** ship any of the features it grades (no bundle projector, no NLI check, no argumentation rules). Those are S1–S8.
- The gold annotation pass (human-verified spans, warning labels) is scoped here as a one-time fixture build; its size is Open Question 5 in the roadmap.

## Requirements

See `specs/kg-prose-eval/spec.md` (EARS). Summary:

| REQ id | Pattern | One-line |
|---|---|---|
| REQ-EVAL-001 | Ubiquitous | Benchmark task = ledger snapshot + chapter contract + gold side-products, committed and frozen |
| REQ-EVAL-002 | Ubiquitous | Metrics module computes attribution / factuality / reasoning / contradiction / rigor / fusion families |
| REQ-EVAL-003 | Event-driven | When the harness runs a task, it emits both prose and the graph-structured side products |
| REQ-EVAL-004 | Ubiquitous | Every metric over every frozen task is result-set-equal to a committed golden under canonical ordering |
| REQ-EVAL-005 | Optional | Where a sprint declares a comparative metric, the harness records both arms and reports the delta |
| REQ-EVAL-006 | State-driven | While gold spans are absent for a task, attribution metrics report `unscored`, not a false zero |
| REQ-EVAL-007 | Unwanted | If a metric run is non-deterministic across two invocations on one snapshot, the harness fails loudly |

## Out of scope

- Live-LLM scoring in the metric path (tests pass a stubbed `llm_call`; the harness itself is deterministic).
- The features under measurement (S1–S8).
- Publication of benchmark numbers as a release gate (advisory until S8 stabilizes the rule surface).
