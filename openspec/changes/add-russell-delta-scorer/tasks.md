# Tasks — Russell-Delta scorer

Lightweight checklist. The exhaustive TDD plan lives at
`docs/plans/2026-05-27-russell-delta-scorer.md` (written via writing-plans).

- [ ] Builder TDD: fixtures → MFW ordering, mean/stdev, determinism
      (REQ-DELTA-002, REQ-DELTA-006)
- [ ] Fetch the ~18 curated public-domain works via scrapling-fetch into a local cache
      (try .txt, fall back to HTML strip); clean Gutenberg boilerplate (REQ-DELTA-009)
- [ ] Build and commit `assets/russell-delta-profile.json` (stats only)
      (REQ-DELTA-001, REQ-DELTA-009)
- [ ] Scorer TDD: equal-to-segment within band; AI-slop above p90; hand-computed
      3-MFW cosine-delta; min-length guard; determinism
      (REQ-DELTA-003, REQ-DELTA-004, REQ-DELTA-005, REQ-DELTA-006)
- [ ] Confirm advisory-only: no gate/fail wiring (REQ-DELTA-007)
- [ ] Add one advisory line to `style_pass_report.py` + template (REQ-DELTA-008)
- [ ] Run russellian-style suite; confirm no regressions
- [ ] Sanity check: score the prior generated math essay and a real Russell excerpt;
      record the two Delta numbers in the change notes

## Sanity results (2026-05-27, classic Burrows's Delta)

The first cut used cosine-to-segments and did not discriminate (real Russell, imitation,
and alien corporate prose all scored ~1.0). The metric was switched to classic Burrows's
Delta (mean absolute z-score to the author profile). Russell's own per-segment band:
p10 = 0.620628, p50 = 0.684914, p90 = 0.786404, max = 1.101273 (444 segments). Outside
fence = p90 + (p90 − p10) = 0.952.

| text | delta | verdict | reliable |
|------|-------|---------|----------|
| Real Russell (`real-russell-math.md`, 1820 words) | 0.791921 | at the edge of Russell's range | true |
| AI imitation (`generated-math-history.md`, 1819 words) | 0.832535 | at the edge of Russell's range | true |
| Alien corporate prose (`alien-sample.md`, 1044 words) | 1.043138 | outside Russell's range | true |

The metric now discriminates: the alien sample (1.043) is clearly outside, while the two
Russell-adjacent texts sit at the edge, correctly ordered (real Russell 0.792 < imitation
0.833 < alien 1.043). The real excerpt lands just past p90 because it is an unusually
logic-dense essay and shorter than the 2500-word segment unit; "at the edge" is the
honest call. Open follow-ups for sharper separation: a contrastive reference corpus
(Russell vs. other authors) and feature-set tuning.
