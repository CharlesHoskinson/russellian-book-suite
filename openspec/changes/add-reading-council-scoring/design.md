# Design — reading council scoring

Full design: `docs/specs/2026-05-27-reading-council-scoring-design.md`.

## Technical approach

Extend `review-conductor`. A craft-grounded rubric (4 dimensions x 1-5) is scored by the
existing persona council via the existing caller-provided dispatcher; a new
`aggregate_reading_scores` takes the median per dimension and emits one synthesized
`reading-score.json`. Flesch Reading Ease and a local burstiness measure are computed
deterministically and reported alongside (not blended). A `documentation` panel points
the council at repo docs.

## Key decisions

- Lives in review-conductor (the council already lives there) — not a new skill.
- Enjoyment is anchored to the Narrative Transportation facets + Stein's
  "defies interruption"; the metric is the calibrated rubric score, deterministic
  readability reported as context.
- Median aggregation across personas (robust to one outlier judge).
- Single synthesized verdict; no per-persona transcript surfaced (project standard).
- Burstiness/Flesch computed locally (small stdlib functions) to avoid spaCy and
  cross-skill coupling in the scorer.
- Advisory; dispatcher injected; deterministic + offline aggregation.

## Rejected alternatives

- Standalone reading-council skill: duplicates the council/dispatch machinery.
- Blended composite enjoyment number: arbitrary weights obscure what drives the score.
- Purely deterministic enjoyment proxy: can't judge style/quality (the closer-uniformity
  lesson).

## Test approach

Stubbed dispatcher with fixture per-persona scores -> assert median aggregation,
synthesized single-verdict shape, anchors present, no per-persona leakage. Flesch and
burstiness unit-tested on known inputs. Deterministic; no network; no live LLM.
