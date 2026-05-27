# Add voice calibration to mode system prompts

## Why

The three mode prompts under `skills/russellian-style/assets/system-prompts/` are
loaded verbatim into composition. They carry negative constraints and structural
mandates but no calibration: no reference to the corpus's rhetorical-move vocabulary,
no exemplar anchor, and dry-understatement guidance only in `polemic.md`. The corpus
map names "paragraph motion: concession, example, distinction, consequence, and turn"
as the target, but the prompts never ask the drafter to plan it.

This change sharpens the input to composition. It adds no gate and weakens none; the
linters and personas remain the enforcers.

## What changes

- Append a `# Calibration and planning` section to each of `technical-exposition.md`,
  `narrative-editorial.md`, `polemic.md`: a silent paragraph-motion planning directive,
  mode-matched move anchors cited from `russell-corpus-map.md`, one contrastive
  touchstone (flat-AI vs. a verified public-domain Russell quote), and an
  understatement line for the two modes lacking one.
- Add `tests/test_system_prompt_calibration.py` asserting the calibration contract for
  every mode.
- Add a validation bundle under `docs/audits/2026-05-27-russellian-voice-calibration/`.
- Register the `VOICE` capability slug in `openspec/README.md`.

## What does not change

`system_prompt_loader.py`, `VALID_MODES`, `DEFAULT_MODE`,
`assets/russell-corpus/index.json`, `references/russell-corpus-map.md`, and every
linter and audit script. Corpus growth stays with `tools/build-russell-corpus`.

## Design

See `docs/specs/2026-05-27-russellian-voice-calibration-design.md`.
