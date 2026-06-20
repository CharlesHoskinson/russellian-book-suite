# Spec delta — triadic-voice

Capability: `TRIAD` (triadic-voice)
Delta against `openspec/specs/triadic-voice/spec.md` (new capability; all ADD).
The v1 `triadic-voice` skill is frozen; these requirements describe the new
`triadic-voice-v2` skill.

## ADD REQ-TRIAD-001 — Ubiquitous

The triadic-voice-v2 skill shall classify each generation prompt into a register
(technical-exposition, narrative-editorial, polemic) and shall select the matching
register dial set.

## ADD REQ-TRIAD-002 — Ubiquitous

The skill shall provide a chassis library of at least six archetypes —
objection→decomposition→verdict; definition-correction→worked-case→consequence;
concrete-scene→abstraction→boundary-condition; false-slogan→causal-account→exact-
replacement; inverted-funnel (Russell-open); and Feynman-sandwich (Feynman-open and
close) — and shall select among them rather than always using the fixed
open-Hoskinson / develop-Feynman / close-Russell sequence.

## ADD REQ-TRIAD-003 — Event-driven

When generating, the skill shall inject profile-derived statistical targets
(sentence-length distribution bands, discourse-marker and direct-address rates,
example spacing) drawn from `hoskinson-style-profile.json` for the chosen register.

## ADD REQ-TRIAD-004 — Ubiquitous

The skill shall retrieve corpus exemplars by the tuple {register, rhetorical move,
stance, cadence pattern, device family} rather than by topic and move alone.

## ADD REQ-TRIAD-005 — Ubiquitous

The skill shall generate by a per-beat plan-then-adapt loop: plan the chassis beats,
draft each beat, self-check the beat against the floor and the advisory signals, then
adapt — rather than producing the whole passage in one pass.

## ADD REQ-TRIAD-006 — Unwanted behaviour

If a generated passage's lemma-trigram or POS-trigram overlap with any corpus
exemplar exceeds a conservative threshold, or it reproduces a taboo verbatim phrase,
then the anti-copy alarm shall fire and the beat shall be regenerated.

## ADD REQ-TRIAD-007 — Ubiquitous

The v1 `triadic-voice` skill shall remain unchanged so it can serve as the 20×20
control; v2 behaviour shall live entirely in `triadic-voice-v2`.
