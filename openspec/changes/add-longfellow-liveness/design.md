# Design — add-longfellow-liveness

Full design: `docs/specs/2026-05-27-longfellow-liveness-design.md`. This file records the
technical approach and the decisions that shaped the spec deltas.

## Approach

Extend the existing vitality program; do not fork it.

- **Prompt liveness layer (`VOICE`).** The change's real effect is calibration text. Each
  mode prompt gains a `## Liveness` subsection of gradable directives at a per-mode dial.
  The directives are drive-oriented craft (percussion, cumulative construction,
  knot-and-resolution, argument-tied anaphora, one concrete anchor per abstraction), not
  ornament. Anchors quote only public-domain Longfellow; in-copyright prose models
  (Carson, Dillard, Eiseley) are referenced by technique only.
- **Ornament guard (`VOICE`).** `lint_ornament.py` is pure-regex, advisory, quote-excluding,
  and spaCy-free. It inverts the Goodhart trap: the suite already rewards concrete
  instances; this penalizes decoration.
- **Measurement (`VOICE-EVAL`).** Add an order-sensitive nPVI cadence signal (stdlib) and a
  liveness summary composed from `lint_paragraph_motion` + `lint_concrete_instance_density`
  + nPVI, minus the ornament penalty. Report before/after as telemetry only.
- **Validation.** A blind reading-council A/B is the success gate: flow and enjoyment rise
  without quality falling. Deterministic signals do not certify liveness.

## Key decisions

- **nPVI, not Fano factor, for cadence.** Fano is permutation-invariant and cannot measure
  rhythm (an ordering phenomenon). nPVI is adjacent-pair contrast, with a sentence-length
  floor to resist fragment-stuffing.
- **Reward instances, penalize jewels.** Imagery is argument-anchored concrete-instance
  density (existing), balanced by the ornament penalty — not raw sensory-noun count, which
  would reward the decorative failure mode.
- **No "beats baseline" claim.** Calibrating a floor from austere Russell prose then
  clearing it is uninformative; the council, not the score, judges improvement.
- **Corpus building lives in `tools/`** and reaches the network only through scrapling-fetch
  (subprocess CLI), preserving the suite's network-boundary invariant. Verse is referenced
  by verified snippet + structural locator, never `line_hint`-into-HTML.

## CI constraint

New code must import cleanly under the `[ci]` extra, which omits the spaCy model. The
ornament linter and the nPVI signal import nothing from `lint_common` (which imports spaCy
at module top); they use stdlib only. Tests that exercise spaCy-backed linters are guarded
with the established `_spacy_model_available()` skip.

## Rejected

A new `voice-liveness` capability and a standalone composite scorer (duplicates the
vitality program); Fano-factor cadence (order-blind); a sensory-concreteness lexicon
(new instrument, deferred); a hard ornament gate (advisory in v1 by convention).
