# Tasks — reading council scoring

Lightweight checklist. The exhaustive TDD plan lives at
`docs/plans/2026-05-27-reading-council-scoring.md` (written via writing-plans).

- [ ] Deterministic anchors TDD: `flesch_reading_ease` (known value) and `burstiness`
      (uniform vs varied) (REQ-READING-006, REQ-READING-008)
- [ ] `aggregate_reading_scores` TDD: median per dimension + overall; single synthesized
      verdict; anchors attached; NO per-persona leakage (REQ-READING-004, REQ-READING-005)
- [ ] `build_scoring_packet`: requests four 1-5 scores + one-line justification vs the
      rubric; dispatcher is injected (REQ-READING-003, REQ-READING-008)
- [ ] `assets/reading-rubric.md` (4 dimensions, craft-anchored 1-5) + reading-score
      schema (REQ-READING-001)
- [ ] `panels/documentation.yaml` (artifact_scope documentation) (REQ-READING-002)
- [ ] Confirm advisory-only (no gate/raise on scores) (REQ-READING-007)
- [ ] Run review-conductor suite; confirm no regressions
- [ ] Demo: score a real repo doc (e.g., README.md) with a stubbed/foreground council;
      record the reading-score.json under docs/audits/2026-05-27-reading-council/
