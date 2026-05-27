# Add a Russell-Delta advisory style-similarity scorer

## Why

The russellian-style linters count deviations from a codified style ideal; none measure
proximity to Russell's actual prose. A head-to-head comparison showed real Russell
tripping the linters 93 times to a machine imitation's 51, because several budgets are
stricter than Russell's own practice. The suite cannot answer "how close is this to
Russell?" This change adds a positive, deterministic answer from stylometry (classic Burrows's
Delta — mean absolute z-score against the author profile), reported as an advisory
metric.

## What changes

- `scripts/build_delta_profile.py`: a network-free builder that turns local cleaned
  Russell texts into a reference profile.
- `assets/russell-delta-profile.json`: a committed reference profile holding statistics
  only (MFW list, per-feature mean/stdev, per-segment z-vectors, internal pairwise-Delta
  distribution, provenance).
- `scripts/score_russell_delta.py`: a deterministic, offline scorer that reports a
  document's Burrows-Delta distance to Russell with an interpretive band and three-band
  verdict.
- One advisory line in `style_pass_report.py` / `style-pass-report.template.md`.
- Tests for builder and scorer (including a hand-computed example); no network in tests.
- Register the `DELTA` capability slug in `openspec/README.md`.

## Reference corpus

Built from 19 curated public-domain Russell prose works enumerated via scrapling-fetch
(ids in the design doc), excluding Principia Mathematica (symbol-dense), the PG index,
the Modern Essays anthology, and non-Russell texts. The larger base is the accuracy
lever.

## What does not change

The metric is advisory only: it adds no gate and blocks nothing. No linter, schema,
loader, or corpus-index change. Source fetching is a separate documented step; the
builder and all tests are network-free.

## Design

See `docs/specs/2026-05-27-russell-delta-scorer-design.md`.
