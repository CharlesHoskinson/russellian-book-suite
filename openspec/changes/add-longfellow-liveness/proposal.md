# Blend Longfellow liveness into the russellian voice

## Why

The russellian-style voice is compliant but reads as "more decorative than Russell" —
strong in spirit, weaker in execution, because too many paragraphs run the same jeweled
circuit. We want the writer livelier: rhythmic drive, forward momentum, argument-anchored
concrete image — without amplifying the decoration that was the diagnosed fault.

The donor is Henry Wadsworth Longfellow, for his rhythm, momentum, and concrete imagery;
his sentiment, archaism, apostrophe, and ornament are firewalled. The repo already ships a
vitality program (`references/russellian-vitality-guide.md`, `lint_paragraph_motion.py`,
`lint_burstiness.py`, `lint_concrete_instance_density.py`), so this change **extends and
composes** it rather than building a parallel scorer.

## What changes

- Append a `## Liveness` subsection to each mode prompt's `# Calibration and planning`
  block (`technical-exposition.md`, `narrative-editorial.md`, `polemic.md`) at a per-mode
  intensity (technical = low, narrative = high, polemic = medium): gradable, drive-oriented
  craft directives (sentence-length percussion, base-clause-first cumulative construction,
  knot-and-resolution cadence, argument-tied anaphora, one concrete anchor per
  abstraction), each with a verified liveness anchor and the firewall.
- Add `references/longfellow-liveness-map.md`: the derived prose-translatable techniques,
  anchors, and firewall, framed "borrow cadence and image-logic, never meter, rhyme,
  archaism, or sentiment."
- Add `tools/build-longfellow-corpus/`: a run-once dev tool that pulls public-domain
  Longfellow from Gutenberg through scrapling-fetch's CLI (subprocess), segments verse,
  and emits `assets/longfellow-corpus/index.json` (pointers + verified snippets +
  structural locators + technique tags).
- Add `scripts/lint_ornament.py`: a pure-regex, advisory decoration guard (purple-prose
  markers, quote-excluding, no spaCy import).
- Extend `scripts/voice_eval.py`: an order-sensitive nPVI cadence signal (stdlib) and a
  liveness summary composed from existing linters minus an ornament penalty, reported
  before/after — as telemetry, with no "beats baseline" claim.
- Add tests for the ornament linter, the nPVI signal, the liveness composite, and the
  per-mode liveness contract.
- Add a validation bundle under `docs/audits/2026-05-27-longfellow-liveness-before-after/`:
  a blind reading-council A/B (baseline vs. blended).

## What does not change

No new capability; `VOICE` and `VOICE-EVAL` are extended only. `system_prompt_loader.py`,
`VALID_MODES`, `DEFAULT_MODE`, the Russell corpus index and map, and the Russell-Delta
scorer are unmodified. Burstiness and concrete-instance density are reused, not
re-implemented. The reading-council scripts are used as-is. No gate is added; all new
signals are advisory.

## Design

See `docs/specs/2026-05-27-longfellow-liveness-design.md`.
