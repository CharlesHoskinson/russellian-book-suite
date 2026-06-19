---
name: liveliness-signals
description: Advisory positive prose signals (cadence, verb-energy, concreteness, curiosity, analogy, cohesion, worked-case) plus the Hoskinson corpus style-profiler for HFR v2. Use to score a passage's liveliness or to (re)build the corpus profile. Advisory only — never a gate in phase 1.
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
---

# liveliness-signals

Positive, advisory paragraph-level signals for HFR v2, plus the corpus profiler
that derives per-register cadence/diction/device statistics from the Hoskinson
corpus. The negative floor stays in `russellian-style`; this skill never gates in
phase 1.

## What it owns
- The corpus style-profiler and `assets/hoskinson-style-profile.json` (stats only).
- Eight advisory paragraph scorers (added in Plan 3).

## What it does NOT own
- The negative discipline floor — `russellian-style`.
- Generation — `triadic-voice` / `triadic-voice-v2`.

## Usage
Build the profile: `python -m scripts.build_corpus_profile`
