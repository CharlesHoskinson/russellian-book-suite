---
name: triadic-voice-v2
description: HFR v2 generator. Same in-session Russell+Feynman+Hoskinson fusion as triadic-voice, but register-routed, chassis-varied, and profile-target-driven, with an anti-copy self-check. Use when generating v2 passages for the HFR comparison. The running model is the generator; no API key.
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
---

# triadic-voice-v2

The v2 HFR generator. Same fused Russell+Feynman+Hoskinson voice and same in-session
doctrine as `triadic-voice` (the running model writes; no API key), but generation is
register-routed, chassis-varied, profile-target-driven, and anti-copy-checked. The v1
`triadic-voice` skill is unchanged and remains the comparison control.

## How to generate (in-session)

1. **Build the brief.** Call `build_generation_brief(topic, rotation)` (from `skill_api`).
   It returns the `register`, a `chassis` (beat plan), numeric `targets` + an injectable
   `targets_prompt`, and an `exemplar_query`. `rotation` increments per passage so the
   chassis varies across a batch.
2. **Ground in the real voice.** Read 6–10 Hoskinson corpus entries matching the
   `exemplar_query` (register + rhetorical move) and the fusion guide
   `../russellian-style/references/triadic-voice-guide.md`. Study cadence; never copy wording.
3. **Plan, then adapt, beat by beat.** Write the passage following the chassis `beats` in
   order. After each beat, check it against the `targets_prompt` (cadence band, direct
   address, example spacing, modifier budget) and the discipline floor; revise the beat
   before moving on. This is the plan-then-adapt loop — not one-shot.
4. **Self-check copying.** Run `anti_copy.check(draft, corpus_texts, taboo)` on the finished
   draft. If `alarm` is true, rewrite the flagged spans — never ship a verbatim corpus run.
5. **Clear the floor.** The passage must pass the `russellian-style` v2 floor for its
   register (`--ruleset russellian-rules-v2.json --register <register>`). Liveliness signals
   are advisory, not gates.

## What v2 changes vs v1
Register routing (technical/narrative/polemic dials), a rotating six-archetype chassis
(not the fixed open-Hoskinson/develop-Feynman/close-Russell), corpus-derived numeric
targets injected into the write, and an explicit anti-copy gate.

## Helpers
`scripts/register_router.py`, `scripts/chassis.py`, `scripts/profile_targets.py`,
`scripts/anti_copy.py`, `scripts/brief.py`. All stdlib, deterministic, unit-tested.
