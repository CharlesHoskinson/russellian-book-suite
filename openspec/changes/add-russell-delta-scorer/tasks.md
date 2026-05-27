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

## Sanity results (2026-05-27)

Profile internal band: p10 = 0.83951, p50 = 1.019974, p90 = 1.138784 (98,346 segments).

| text | delta | p50/p90 band | verdict | reliable |
|------|-------|-------------|---------|----------|
| Real Russell (`real-russell-math.md`, 1820 words) | 1.001321 | within (< p90 1.14) | within Russell's range | true |
| AI imitation (`generated-math-history.md`, 1819 words) | 0.996431 | within (< p90 1.14) | within Russell's range | true |
| Alien corporate prose (`alien-sample.md`, 1044 words) | 0.996780 | within (< p90 1.14) | within Russell's range | true |

The metric does not discriminate at all between real Russell, AI imitation, and alien corporate/SaaS prose: all three deltas cluster between 0.996 and 1.001, well below the p90 threshold of 1.138. This is a real finding, not a scoring artefact. Absolute cosine-delta against a single-author profile at this feature dimensionality lacks the discriminative power to separate stylistically distant registers, likely because function-word frequency distributions converge across formal English writing styles regardless of genre. A follow-up should investigate per-segment normalization (Evert et al. approach), expansion of the MFW feature set beyond the 150-word profile, or a contrastive reference corpus to compute relative (not absolute) delta distances.
