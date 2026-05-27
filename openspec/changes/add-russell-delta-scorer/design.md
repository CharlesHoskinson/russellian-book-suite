# Design — Russell-Delta scorer

Full design: `docs/specs/2026-05-27-russell-delta-scorer-design.md`.

## Technical approach

Cosine-Delta over the top-N (default 300) most-frequent words, computed against a
committed reference profile built from ~18 public-domain Russell prose works. The score
is the mean cosine distance between the target's z-vector and each reference segment
z-vector (document-to-document, not document-to-centroid, since the centroid is zero in
z-space where cosine is undefined). An internal pairwise-Delta band gives the verdict.

## Key decisions

- Advisory only; no gate (Delta is a distance, not a correctness check; a single
  threshold is brittle and gameable).
- Committed asset stores statistics only, no prose — consistent with the corpus index
  policy.
- Builder is network-free and consumes local files; fetching is a separate documented
  step via scrapling-fetch (try .txt, fall back to HTML strip for HTML-only works).
- Cosine Delta over Manhattan Delta (Evert et al.: better discrimination).
- N=300 default supported by the enlarged corpus; segment size ~2500 words.
- Reuse `lint_common.load_markdown`; invoke like the linters (`python -m scripts...`).

## Rejected alternatives

- Classic Manhattan Delta only: simpler but less discriminating.
- Neural style-embedding similarity: heavy, opaque, non-deterministic; clashes with the
  suite's deterministic-asset ethos.
- Hard or soft gating on Delta: deferred; advisory-first until real Delta distributions
  are observed.

## Test approach

Builder and scorer under TDD with fixtures and a hand-computed 3-MFW example for the
cosine-delta math. No network in tests. Determinism asserted.
