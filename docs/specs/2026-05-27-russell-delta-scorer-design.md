# Russell-Delta advisory style-similarity scorer

Date: 2026-05-27
Status: proposed
Capability: russell-delta (`DELTA`)

## Problem

The russellian-style linters count deviations from a codified, austere style ideal.
They do not measure proximity to Russell's actual prose. A head-to-head run made this
concrete: a length-matched excerpt of Russell's own "Mathematics and the
Metaphysicians" tripped the twelve linters 93 times against 51 for a machine
imitation, because the budgets for signal density, passive voice, and sentence rhythm
are stricter than Russell's own practice. Nothing in the suite answers the question a
reader actually asks: how close is this prose to Russell?

This change adds a positive, deterministic, content-independent answer drawn from
stylometry: a Russell-similarity score based on Burrows's Delta.

## Background

Burrows's Delta represents a text by the z-scored relative frequencies of the most
frequent words (function words dominate the list), and measures stylistic distance in
that space. Function-word signatures are stable within an author and robust to topic.
Evert et al. showed that the cosine variant ("Cosine Delta") discriminates better than
the original Manhattan Delta. The metric is the established standard for authorial
stylistic proximity, it is deterministic, and it needs no model — a good fit for a
suite whose discipline is deterministic gates.

References: Burrows 2002; Argamon, geometric/probabilistic foundations; Evert et al.,
"Understanding and explaining Delta"; "Improving Burrows's Delta."

## Scope

In scope: a profile builder, a committed reference-profile asset, the scorer, one
advisory line in the style report, and tests.

Out of scope (explicit follow-ups): gating on Delta; corpus-grounded recalibration of
the budget linters; the LLM rubric "virtues" judge; detector-precision fixes.

## Design

### Reference corpus

The profile is built from a curated set of public-domain Russell prose works on Project
Gutenberg, enumerated via `scrapling-fetch`. Genuine Russell prose is kept; works that
would corrupt word-frequency stylometry or are not Russell are excluded.

Keep (19 works, by Gutenberg id): 5827, 25447, 37090, 2529, 4776, 44932, 13940, 690,
77894, 41654, 17350, 72981, 67104, 73782, 70302, 55610, 66225, 52091, 77427.

Exclude: 78050 and 78255 (Principia Mathematica vol. 1-2 — symbol-dense), 59391 (PG
index), 38280 (Modern Essays anthology), 5740 (Wittgenstein), 17771 (Santayana).

A larger base is the accuracy lever: more text yields stabler per-feature mean and
standard deviation, a more robust author centroid, and a well-populated internal-Delta
distribution.

### Reference profile asset

`assets/russell-delta-profile.json` stores statistics only, no source prose (honoring
the corpus index's frequencies-only policy):

- `mfw`: the top-N most-frequent words across the reference corpus, ordered (N default
  300).
- `mean`, `stdev`: per-feature mean and standard deviation of relative frequency across
  reference segments.
- `segments_z`: the z-vector of every reference segment (the matrix used for the
  doc-to-segments comparison).
- `internal_delta`: the distribution of pairwise Cosine Delta among reference segments
  (p10, p50, p90, max) — Russell's own internal variation, used as the interpretive
  band.
- Provenance: `method`, `n_features`, `segment_words`, `tokenizer`, `source_policy`,
  `reference_ids`, `built_at`.

### Builder

`scripts/build_delta_profile.py` is network-free. It consumes local cleaned text files,
strips Gutenberg boilerplate, segments each work into ~2500-word units, computes the
MFW list and per-feature mean/stdev across segments, computes each segment's z-vector
and the internal pairwise-Delta distribution, and writes the asset deterministically.

Fetching the sources is a separate documented step that uses `scrapling-fetch`: it
tries the plain-text Gutenberg path and falls back to fetching the HTML and stripping
tags for HTML-only works (e.g., 41654). Keeping fetch and compute separate keeps the
builder testable with fixtures and free of network in CI.

### Scorer and the metric

`scripts/score_russell_delta.py` runs like the linters
(`python -m scripts.score_russell_delta <file.md>`):

1. `lint_common.load_markdown` to text; lowercase; tokenize on `[a-z']+`.
2. Compute relative frequency of each profile MFW; z-score with the profile
   mean/stdev to get the target z-vector **t**.
3. Score = mean over reference segments of the cosine distance `1 - cos(t, s_i)`.
   Cosine Delta is computed document-to-document, not document-to-centroid: the author
   centroid is approximately zero in z-space, where cosine is undefined, so the target
   is compared against each reference segment z-vector and averaged.
4. Compare the score to `internal_delta` to yield a verdict: `within Russell's range`
   when at or below the band's upper reaches (>= p90 is `outside`), else proportional
   reporting against p10/p50/p90.
5. Below the minimum reliable length (default 1000 words) the score is still reported
   with `reliable: false`.

Output JSON: `{"metric":"russell-cosine-delta","delta":<float>,"band":{"p10","p50",
"p90"},"verdict":<str>,"n_words":<int>,"reliable":<bool>}`. Pure Python (`Counter`,
`math`), deterministic, offline.

### Report integration

`style_pass_report.py` and `style-pass-report.template.md` gain one advisory line that
prints the Delta score and verdict. It does not gate; it informs.

## Testing

Builder: tiny fixture texts produce a profile with the correct MFW ordering and
mean/stdev; output is deterministic for fixed input.

Scorer:
- a text equal to a reference segment scores within the band;
- a modern machine-prose paragraph scores above p90 (`outside`);
- a 3-MFW, 2-segment hand-computed example yields the exact known cosine-delta value;
- the minimum-length guard sets `reliable: false`;
- repeated runs on the same input are identical.

No network in any test.

## Consistency with the suite

The scorer is advisory and adds no gate, so it cannot block a chapter (REQ). It follows
the linter invocation pattern and reuses `lint_common.load_markdown`. The asset stores
statistics only, consistent with the corpus index policy. The metric is deterministic,
consistent with the suite's gate philosophy and its no-live-LLM test rule.
