# Design — Russell-Delta scorer

Full design: `docs/specs/2026-05-27-russell-delta-scorer-design.md`.

## Technical approach

Classic Burrows's Delta (mean absolute z-score of the target's top-N=300 most-frequent-
word frequencies against the author profile) computed against a committed reference
profile built from 19 public-domain Russell prose works. The verdict compares the
target's Delta to the distribution of Russell's own per-segment Deltas (`centroid_delta`)
in three bands. (A cosine-to-segments variant was tried first and failed to discriminate
— in high-dimensional z-space all formal English scored ~1.0 — so the metric was
switched to the classic single-author Delta.)

## Key decisions

- Advisory only; no gate (Delta is a distance, not a correctness check; a single
  threshold is brittle and gameable).
- Committed asset stores statistics only, no prose — consistent with the corpus index
  policy.
- Builder is network-free and consumes local files; fetching is a separate documented
  step via scrapling-fetch (try .txt, fall back to HTML strip for HTML-only works).
- Classic Burrows's Delta (mean |z| to author profile) for single-author distance;
  cosine variants suit multi-author attribution, not a one-author proximity score.
- Three-band verdict with fence = p90 + (p90 − p10): p90 alone false-flags genuine
  Russell, `max` is outlier-inflated.
- N=300 default supported by the enlarged corpus; segment size ~2500 words.
- Reuse `lint_common.load_markdown`; invoke like the linters (`python -m scripts...`).

## Rejected alternatives

- Cosine-to-segments delta: tried and abandoned — no discrimination (all formal English
  ~1.0 in high-dim z-space).
- Neural style-embedding similarity: heavy, opaque, non-deterministic; clashes with the
  suite's deterministic-asset ethos.
- Hard or soft gating on Delta: deferred; advisory-first until real Delta distributions
  are observed.

## Test approach

Builder and scorer under TDD with fixtures and hand-built stub profiles for the verdict
bands. No network in tests. Determinism asserted.
