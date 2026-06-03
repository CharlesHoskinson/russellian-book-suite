---
name: feynman-style
description: Rewrite already-Russellized technical prose in Richard Feynman's voice — concrete analogy and physical intuition, conversational directness, honest curiosity, plain playful diction — without altering the argument. Use when user says "apply Feynman style", "make this click", "warm up this prose", "explain this simply", "Feynman pass on this draft", or asks to lower reading difficulty after a Russell pass. Do NOT use before russellian-style, and do NOT use for formal proofs, legal/specification text, API reference, bureaucratic boilerplate, or academic abstracts.
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
---

# feynman-style

Second pass after `russellian-style`. Russell makes prose correct, atomic, and hedge-free but dense; this skill warms the surface so it clicks for a reader. The argument is fixed by Russell and must survive untouched.

## The two-layer contract

- **Feynman owns the prose surface.** It may re-introduce what Russell strips: rhetorical questions, asides, contractions, direct address, "now you might ask—", honest-doubt framing.
- **Russell owns the argument skeleton.** Feynman must not change claims, claim accuracy, logical structure, or atomic argument order. `preserve_argument` enforces this as a hard gate.

## What it owns

- Surface readability: analogy, concreteness, reading grade, conversational diction, curiosity.
- The Feynman voice prompts and rule registry.
- The Surface/Integrity linter partition (which Russell checks may run on Feynman-final text).
- `preserve_argument` — the claims/structure survival gate.

## What it does NOT own

- Source ingestion, claim ledgers — `book-knowledge`.
- Chapter drafting, release bundles — `book-compose`.
- The Russell discipline itself — `russellian-style`.
- Generic AI tells (em-dash overuse, rule-of-three) — `humanizer`.

## Linters

- `lint_reading_grade.py` — Flesch-Kincaid grade load; flags too-hard sentences.
- `lint_conversational.py` — rewards direct address, contractions, rhetorical questions.
- `lint_latinate_diction.py` — flags Latinate jargon with a plain Anglo-Saxon alternative.
- `lint_concreteness.py` — analogy markers + concrete-instance density; flags ungrounded abstraction.
- `lint_curiosity_markers.py` — rewards honest-doubt / puzzle framing.
- `lint_sentence_rhythm.py` — cadence/burstiness, ported from russellian-style (Feynman threshold recalibration deferred).
- `lint_ai_vocabulary.py` — AI-slop vocabulary guard (ported).

## Calibration

Generation is prompt-driven. Linters use absolute thresholds from `assets/feynman-rules.json`. An optional relative-frequency distance scorer (`score_feynman_delta.py`) compares against `assets/feynman-delta-profile.json` using an L1 distance over word frequencies; the profile is hand-set by default and can be rebuilt offline by `build_delta_profile.py` from copies the user drops in a git-ignored `corpus-raw/` folder. The skill ships and runs with zero network access.
