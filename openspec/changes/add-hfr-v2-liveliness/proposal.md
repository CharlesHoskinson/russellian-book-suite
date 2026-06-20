# Add HFR v2 — liveliness signals, floor calibration, chassis variation, 20×20 test

## Why

The suite enforces a negative discipline floor that removes AI tells but cannot
certify that prose is alive. Two failure modes are documented on the sample
artifact (`examples/triadic-trust-decomposition.md`): a passage clears every floor
linter and still reads mechanical (pass-but-flat), and the floor penalized a
deliberate anaphoric drumbeat while the keyword analogy/curiosity rewards missed
obvious analogy and curiosity that were present. Two deep-research reports plus
eight primary papers (read; in `hfr-deep-research/`) converge on the fix: stop
asking only "is the text defect-free?" and start rewarding *enacted explanation* —
drumbeat, mapping, setup-payoff, action-bearing diction — and move fixed global
budgets to corpus- and register-conditioned corridors. None of this relaxes
Russell.

## What changes

- **New skill `liveliness-signals`**: a corpus profiler emitting
  `assets/hoskinson-style-profile.json` (statistics only, per register), and eight
  advisory paragraph-level scorers (cadence corridor, verb-energy, concrete-anchor,
  subject-verb distance, curiosity setup-payoff, analogy-mapping, novelty-continuity,
  worked-case presence).
- **`russellian-style` v2 ruleset** (`assets/russellian-rules-v2.json`, selected by
  `--ruleset`/`--register`): a rhythm drumbeat exemption and a register-conditioned
  modifier corridor replacing the global 0.25 budget. The v1 ruleset is byte-frozen.
- **`feynman-style`**: its keyword analogy/curiosity rewards delegate to the
  structure-based detectors in `liveliness-signals`.
- **New skill `triadic-voice-v2`**: register router, a six-archetype chassis library,
  profile-driven generation targets, retrieval by `{register, move, stance, cadence,
  device}`, a per-beat plan-then-adapt loop, and an anti-copy n-gram alarm. The v1
  `triadic-voice` skill is frozen as the control.
- **New skill `voice-eval`**: the 20×20 comparison harness (floor-clean gate +
  positive-signal metric deltas + blind pairwise in-session judge), a formula-drift
  monitor, and the blind A/B human-study scaffold.
- Register the `LIVE` and `TRIAD` capability slugs in `openspec/README.md`.

## Source-paper corrections applied

1. Verb-energy targets light-verb **constructions**, not nominalization suffixes
   (cmp-lg/9503010) — protects domain nouns.
2. Burstiness uses a two-sided percentile **corridor**, not a lone CV
   (1805.01460) — CV is gameable and blind to rhythm autocorrelation.
3. AI-text detectors **never gate** (2412.05139) — advisory only.
4. Authorial distance is a **distributional proxy**, not a fine-tuned LM
   (2401.12005) — 57 paragraphs is too little to fine-tune.

## What does not change

The negative floor stays hard and separate; every positive signal is advisory in
phase 1 and may graduate to a gate only after the human-correlation study (Spearman
+ bootstrap CI excluding zero, never at the cost of trustworthiness). The v1
`triadic-voice` skill and the v1 `russellian-style` ruleset are frozen, so the 20×20
control is reproducible. No change to `book-knowledge`, the claim ledger, or the
release gate.

## Acceptance test

The 20×20: 20 prompts × {v1, v2}, all 40 floor-clean, scored on the eight signals,
judged blind-pairwise in-session. Success = v2 stays floor-clean, scores higher on
the positive signals, wins >50% pairwise with trustworthiness not worse, and shows
lower formula drift.

## Design

See `docs/specs/2026-06-19-hfr-v2-liveliness-design.md`.
