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
