# KG Prose Eval Harness Design

## Scope

S0 adds a read-only measurement harness for the prose pipeline. The harness lives in
`skills/book-knowledge/scripts/` because it reads graph-era side products and the
append-only claim ledger, but it does not write to a workspace. Its only write target
is `docs/eval/kg-prose/_runs/`.

## Corpus Layout

Each frozen task is stored under `docs/eval/kg-prose/<task-id>/`:

- `task.json`: task id, chapter id, snapshot paths, and declared comparisons.
- `snapshot/`: immutable copy of the ledger snapshot and chapter contract artifacts.
- `gold/`: hand-curated gold data and metric goldens.

The harness reads only this frozen task directory. It never reads `examples/` or a
live workspace. A run hashes the snapshot and gold inputs before and after execution;
tests assert the bytes are unchanged.

## Side-Product Schema

`skills/book-knowledge/assets/kg-prose-side-products.schema.json` declares the single
structured side-product shape emitted by the harness. The fields match the landed
sprints:

- `selected-claims`, `cited-spans`, and `code-links` are copied from the S1
  chapter-retrieval bundle payload.
- `writer-assertions` and `draft-atomic-facts` are copied from S2 book-compose
  artifacts.
- `contradiction-alerts`, `warnings`, `proof-traces`, and `prose` are reserved
  structured outputs for later sprint producers.

The schema is intentionally an evaluation interchange schema, not a new production
record type. It does not relax skill ownership or add a graph relation.

## Metrics

The metrics module returns all six families on every task:

- Attribution: scored now against gold sentence-to-span bindings and S2
  writer-assertion `cites_span` values.
- Factuality: scored now over S2 `draft-atomic-facts` and writer-assertion
  `citation_check_status`, with claim statuses read from the frozen ledger snapshot.
- Reasoning, contradiction, rigor, and fusion: present but `unscored` until their
  producing sprints and gold side products exist.

Factuality partitions every atomic fact into exactly one bucket:

1. `no-claim-binding` when the fact has no claim id.
2. `span-check-failed` when the fact's claim is bound to a writer assertion whose
   citation check is not `full`.
3. `disputed-claim-backed` when the bound claim's latest ledger status is disputed.
4. `verified-claim-backed` for remaining claim-backed facts.

Missing gold returns `unscored` with a reason and does not report zero as a score.

## Comparative Metric

The first comparative metric is S1 claim-first bundle treatment versus a flat claim
list control. It reports both arms as raw coverage counts and a numeric delta. The
metric is descriptive; it does not publish release-gate numbers.

## Determinism

Metric outputs are canonicalized before comparison. The harness has a determinism
guard that executes a metric twice on the same frozen inputs and raises a named error
when canonical outputs differ. Metric goldens are compared after canonical sorting,
so result-set equality does not depend on object insertion order.
