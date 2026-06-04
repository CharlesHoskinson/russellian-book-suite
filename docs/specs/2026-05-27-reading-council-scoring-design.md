# Reading council with an enjoyment metric

Date: 2026-05-27
Status: proposed
Capability: reading-council (`READING`)

## Problem

The suite has a persona council (`book-review` + `review-conductor`) with an Enjoyment
Reader, but it emits severity tags, not scores, and it is chapter-scoped. There is no
quantitative metric of enjoyment, and nothing watches the documentation for stale prose.
This change adds a craft-grounded scoring rubric, runs the existing council against it to
produce enjoyment/flow/style/quality scores, and points it at documentation.

## Scope

In scope: a reading rubric asset, a documentation-scope scoring panel, a scoring
dispatch packet, score aggregation into one synthesized `reading-score.json`,
deterministic anchors reported alongside, a report, and tests.

Out of scope (follow-ups): a recurring all-docs staleness sweep (make target / scheduled
trigger); a book-compose gate; golden-set calibration tuning.

## Design

### Rubric

`review-conductor/assets/reading-rubric.md` defines four dimensions, each scored 1-5
against anchored descriptors drawn from the craft references:

- Enjoyment — Narrative Transportation facets (attention, affect, imagery/vividness) plus
  Sol Stein's page-turner test ("the best reading experiences defy interruption"); 5 =
  could not stop, 1 = abandoned early.
- Flow — momentum and transitions; the paragraph as the unit of composition
  (Strunk-White); sentence rhythm; where the reader snags.
- Style — vigor, concision ("make every word tell"), particularity (Stein), the
  specific/definite/concrete (Strunk-White), voice.
- Quality — clarity, structure, accuracy, earning its length.

References: Strunk & White, The Elements of Style; Sol Stein, Stein on Writing;
Green & Brock (2000) and Appel et al. (2015) on the Narrative Transportation Scale.

### Council, scored

Reuse `review-conductor`'s dispatch and Outcomes exemplar calibration. Add a scoring
panel `panels/documentation.yaml` (`artifact_scope: documentation`) whose personas
(Enjoyment Reader, Gottlieb, Lay Reader, First-Time Visitor) each return the four 1-5
scores plus a one-line justification against the shared rubric. The dispatcher remains a
caller-provided callable, so tests stub it and the scoring makes no live LLM calls of its
own.

### Synthesis (single voice, no transcript)

`aggregate_reading_scores` takes the median per dimension across personas (median is
robust to a single outlier judge), computes an overall score, and emits one
`reading-score.json`:
`{enjoyment, flow, style, quality, overall, deterministic: {flesch, burstiness}, verdict}`.
`verdict` is a single synthesized paragraph in one voice. No per-persona transcript or
quotation appears in the output — the council is internal.

### Deterministic anchors, alongside

`reading_scores.py` computes Flesch Reading Ease and a local burstiness measure (the
ratio of the standard deviation of sentence lengths to their mean) with small,
dependency-free, deterministic functions. They are attached as context and corroborate
or flag drift against the rubric enjoyment score; they are NOT blended into the rubric
scores (no arbitrary weights).

### Components (in `review-conductor/`)

- `assets/reading-rubric.md` — the rubric.
- `assets/reading-score.schema.json` — schema for the output.
- `panels/documentation.yaml` — the documentation scoring panel.
- `scripts/reading_scores.py` — `build_scoring_packet`, `aggregate_reading_scores`,
  `flesch_reading_ease`, `burstiness`, `write_reading_report`.

## Testing

- Stubbed dispatcher returns fixture per-persona score sets; assert median aggregation
  per dimension, the overall, the synthesized single-`verdict` shape, deterministic
  anchors present, and that no per-persona text leaks into the output.
- `flesch_reading_ease` on a known sentence returns the known value (within tolerance).
- `burstiness` on uniform vs varied sentence lengths returns low vs high.
- Determinism: same inputs, same output. No network, no live LLM.

## Consistency with the suite

Advisory only (book-qa / soft-gates remain the gating authorities). Extends
review-conductor's existing panel machinery. The dispatcher is injected (the suite's
no-live-LLM-in-tests convention). Aggregation and anchors are deterministic and offline.
The synthesized-output rule honors the project's "no surfaced agent scaffolding" standard.
