# Tasks — HFR v2

Lightweight checklist. The exhaustive per-component TDD plans are written via the
writing-plans skill as a 5-plan set under `docs/plans/2026-06-19-hfr-v2-liveliness-*`
(Plan 1: corpus-profile is written; Plans 2–5 follow in sequence).
Sequence: profile → floor ruleset → signals → generation v2 → eval.

## Corpus profile (foundation)
- [ ] Profiler TDD: fixtures → per-register percentile corridors, distributions,
      concreteness/light-verb rates, determinism, network-free
      (REQ-LIVE-001, REQ-LIVE-002, REQ-LIVE-014)
- [ ] Build and commit `assets/hoskinson-style-profile.json` (stats only)
      (REQ-LIVE-001)

## Floor calibration (russellian-style v2 ruleset)
- [ ] Add `--ruleset`/`--register`; freeze v1 `russellian-rules.json`
      (REQ-VOICE-008)
- [ ] Drumbeat exemption + `parallel-list` credit under v2; v1 rhythm unchanged;
      regression-test against the sample run (REQ-VOICE-009)
- [ ] Register-conditioned modifier corridor replacing global 0.25
      (REQ-VOICE-010)
- [ ] Accuracy-floor invariant across registers/rulesets; narrow passive end-focus
      exemption (REQ-VOICE-011, REQ-VOICE-012)

## Positive signals (liveliness-signals, advisory)
- [ ] Cadence corridor (two-sided, not lone CV) (REQ-LIVE-005)
- [ ] Verb-energy: light-verb+event-noun constructions + allow-list (REQ-LIVE-006)
- [ ] Concrete-anchor with vendored Brysbaert lexicon + reuse bonus (REQ-LIVE-007)
- [ ] Subject→verb distance; curiosity setup-payoff; analogy-mapping (v1 det,
      v2 embeddings); novelty-continuity coherence; worked-case routing
      (REQ-LIVE-003, REQ-LIVE-008, REQ-LIVE-009, REQ-LIVE-010, REQ-LIVE-011)
- [ ] Advisory-only wiring; WARN-not-skip on missing resource; device challenge
      regression set with the sample as item 1
      (REQ-LIVE-004, REQ-LIVE-012, REQ-LIVE-013)
- [ ] Redirect feynman-style keyword analogy/curiosity to these detectors

## Generation v2 (triadic-voice-v2)
- [ ] Register router; six-archetype chassis library
      (REQ-TRIAD-001, REQ-TRIAD-002)
- [ ] Profile-driven targets; tuple retrieval; per-beat plan-then-adapt loop
      (REQ-TRIAD-003, REQ-TRIAD-004, REQ-TRIAD-005)
- [ ] Anti-copy n-gram/taboo alarm; keep v1 triadic-voice frozen
      (REQ-TRIAD-006, REQ-TRIAD-007)

## Evaluation (voice-eval) — the 20×20 final test
- [ ] 20-prompt stratified set; v1+v2 generation; equal-grounding floor gate
      (REQ-VEVAL-009, REQ-VEVAL-010)
- [ ] Per-signal metric deltas; blind order-swapped in-session pairwise judge with
      win-rate (REQ-VEVAL-011, REQ-VEVAL-012)
- [ ] Formula-drift monitor; detector-never-gates; success-criterion report
      (REQ-VEVAL-013, REQ-VEVAL-014, REQ-VEVAL-015)
- [ ] Human-study scaffold + graduation gate (built; raters are a later run)
      (REQ-VEVAL-016, REQ-VEVAL-017)

## Wiring & housekeeping
- [ ] Register `LIVE` and `TRIAD` slugs in `openspec/README.md`
- [ ] Skill venvs (Python 3.14, spaCy `en_core_web_sm`); `sibling_skills` ABI
- [ ] Run full suite; confirm no regressions; ruff clean before push
- [ ] Run the 20×20; record metric deltas, win-rate, and drift in change notes
