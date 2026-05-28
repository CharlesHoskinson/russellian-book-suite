# Guard the russellian voice against template fatigue

## Why

The Longfellow-liveness blend solved the decoration fault that an external reader
diagnosed in the v1 snails essay. A v3 snails essay produced by the new voice then
received its own reader's verdict: the voice has *one move and runs it sixteen
times* (fact → pivot → aphorism about humanity), the reader's ear learns the meter by
paragraph four, the persona is too pleased with itself, and the diction is
Edwardian-familiar-essay pastiche. The reading council scored v3 4/4/4/4 — the suite
cannot see what the reader saw.

That gap is the next iteration's target. The fault is the Goodhart shape surfacing on
a new axis: not decoration, but **monotony of figure** — the liveness layer specifies a
fixed set of moves and applies them at *high* intensity to every paragraph, so the
writer becomes a metric-shaped author of metric-shaped prose. The corpus calibration
(Carson/Dillard/Eiseley + Longfellow verse) is pre-1960; without a post-1950 prose
model, the writer reaches for the Edwardian register the donors share.

## What changes

- Add `scripts/lint_shape_variance.py`: a stdlib advisory linter that reuses
  `classify_paragraph` from `lint_paragraph_motion` and flags any single paragraph
  shape that occupies ≥5 of any 6-paragraph window, or ≥3 paragraphs in immediate
  succession. Pure stdlib; no spaCy; no `lint_common`.
- Add `scripts/lint_aphorism_density.py`: a stdlib advisory linter that flags
  paragraph-closing sentences matching the fact-→-moral shape (8–18 words,
  humanity-generalising token, no concrete-instance marker). Quote-excluding. Pure
  regex; no spaCy; no `lint_common`.
- Wire both new linters into `voice_eval._linters()` so they appear in the standard
  density table. No change to the liveness composite (the new signals are advisory
  telemetry, surfaced alongside `ornament`, not folded into the rolled-up number).
- Append a **self-turning paragraph mandate** to each mode's `## Liveness` subsection
  (`technical-exposition.md`, `narrative-editorial.md`, `polemic.md`): at least one
  paragraph per essay must complicate, refuse, or turn the irony of the running
  thesis on the essayist, not reinforce it. The mandate is identical across the three
  modes — it is structural, not intensity-scaled — and includes a final clause
  guarding against the break itself becoming a template.
- Add **Joan Didion** to the disciplined-lyricism prose-models section of
  `longfellow-liveness-map.md`: post-1950, in copyright, referenced by named technique
  only (never quoted), describing the flat declarative as anti-aphorism and the
  refusal of the moral. Pattern matches the existing Carson/Dillard/Eiseley entries.
- Extend `tests/test_system_prompt_liveness.py` with one parametrized assertion that
  each mode's `## Liveness` subsection contains the self-turning mandate.
- Add tests for the two new linters (`test_shape_variance.py`, `test_aphorism_density.py`,
  neither named `test_lint_*` so the conftest's spaCy-absent `collect_ignore_glob` does
  not silently skip them in CI).
- Add a validation bundle at `docs/audits/2026-05-28-snails-v3-vs-v3.1/`: a rewritten
  snails essay applying the design + fixing two factual errors caught in the v3
  critique (`Fulvius Lippinus` not `Hirpinus`; the Bernoulli stonemason carved an
  Archimedean spiral instead of the requested logarithmic one), with telemetry and a
  reading-council comparison vs. v3 and the prior bundles.

## What does not change

No new capability; `VOICE` is extended only. `system_prompt_loader.py`, `VALID_MODES`,
`DEFAULT_MODE`, the Russell corpus index and map, the Longfellow corpus index, the
Russell-Delta scorer, the existing `ornament`/`burstiness`/`paragraph_motion`/
`concrete_instance_density`/`hedges`/`passive_voice`/etc. linters, and the
reading-council scoring scripts are all unmodified. The liveness composite formula and
its calibration constants are unchanged — the new signals report alongside, not inside.
No gate is added; both new linters are advisory, matching the v1 vitality convention.

## Design

See `docs/specs/2026-05-28-voice-anti-monotony-design.md`.

## Branch base

`feat/voice-anti-monotony` is based on `feat/longfellow-liveness` (the new change
extends files added there: the per-mode `## Liveness` sections, the
`longfellow-liveness-map.md` reference, the `longfellow-corpus` assets). PR base at
finish time: `feat/longfellow-liveness` (stacked PR) until that branch merges to main,
then rebase onto main.
