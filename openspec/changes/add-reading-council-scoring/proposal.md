# Add a reading council with an enjoyment metric

## Why

The suite's persona council (book-review + review-conductor) emits severity tags, is
chapter-scoped, and has no quantitative metric of enjoyment — and nothing watches the
documentation for stale prose. This change adds a craft-grounded scoring rubric, runs
the existing council against it to produce enjoyment/flow/style/quality scores, and
points it at documentation, to keep the writing from going stale.

## What changes

- `review-conductor/assets/reading-rubric.md` — four dimensions (enjoyment, flow, style,
  quality), 1-5 anchored descriptors grounded in Strunk-White, Sol Stein, and the
  Narrative Transportation Scale.
- `review-conductor/panels/documentation.yaml` — a documentation-scope scoring panel.
- `review-conductor/scripts/reading_scores.py` — scoring dispatch packet,
  `aggregate_reading_scores` (median per dimension), `flesch_reading_ease`, `burstiness`,
  and a report writer producing one `reading-score.json`.
- `assets/reading-score.schema.json`, tests, and the `READING` capability slug.

## What does not change

Scoring is advisory: it gates nothing. The dispatcher is caller-provided (no live LLM
calls; none in tests). The output is a single synthesized verdict with no per-persona
transcript. Deterministic anchors are reported alongside, never blended into, the rubric
scores. Aggregation and anchors are deterministic and offline.

## Design

See `docs/specs/2026-05-27-reading-council-scoring-design.md`.
