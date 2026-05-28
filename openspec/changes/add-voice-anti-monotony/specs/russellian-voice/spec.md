# Spec delta — russellian-voice

Capability: `VOICE` (russellian-voice)
Delta against the `russellian-voice` capability as established by
`add-voice-calibration-prompts` (REQ-VOICE-001..007) and extended by
`add-longfellow-liveness` (REQ-VOICE-008..017); none yet archived to
`openspec/specs/`. All ADD; numbering continues at 018; no renumbering.

## ADD REQ-VOICE-018 — Event-driven

When `lint_shape_variance` runs on a markdown document, it shall split the document
into paragraphs, classify each paragraph via `lint_paragraph_motion.classify_paragraph`,
and emit one finding for each run in which a single shape occupies at least five of
any six consecutive paragraphs, and one finding for each run of at least three
consecutive paragraphs sharing a shape.

## ADD REQ-VOICE-019 — Ubiquitous

`scripts/lint_shape_variance.py` shall import nothing from `scripts.lint_common` and
shall import no spaCy; it shall load and run under the CI `[ci]` extra without the
spaCy English model.

## ADD REQ-VOICE-020 — Event-driven

When `lint_aphorism_density` runs on a markdown document, it shall apply a
quote-exclusion pass (double-quoted spans, curly-quoted spans, and markdown
blockquote lines) and then, for each paragraph, test the paragraph's closing sentence
against the aphorism shape: between 8 and 18 words; containing at least one
humanity-generalising token (`we`, `our`, `us`, `ourselves`, `mankind`, `humanity`,
`civilisation`, `modern life`, `most people`, `most of us`, `the rest of us`,
`none of us`); and containing no concrete-instance marker (a capitalised non-initial
word, a four-digit year, or a numeric quantity). It shall emit one finding per
qualifying closer.

## ADD REQ-VOICE-021 — Ubiquitous

`scripts/lint_aphorism_density.py` shall import nothing from `scripts.lint_common`,
shall import no spaCy, and shall use only the standard library and `re`; it shall
load and run under the CI `[ci]` extra without the spaCy English model.

## ADD REQ-VOICE-022 — Ubiquitous

Both new linters shall be advisory: they shall not gate, fail, or block any pipeline,
and shall record an internal tier for the report only.

## ADD REQ-VOICE-023 — Ubiquitous

Each mode system prompt's `## Liveness` subsection shall contain a self-turning
paragraph mandate requiring that at least one paragraph per essay complicate the
running thesis, refuse it, or turn its irony on the essayist — not reinforce it —
and the mandate shall include a final clause guarding against the break itself
becoming a template. The mandate text shall be identical across the three modes
(structural, not intensity-scaled).

## ADD REQ-VOICE-024 — Ubiquitous

The "Disciplined-lyricism prose models" section of
`references/longfellow-liveness-map.md` shall include an entry for Joan Didion,
referenced by named technique only and not quoted, describing the flat declarative
as anti-aphorism, the concrete list that argues without summarising, and the refusal
of the moral.

## ADD REQ-VOICE-025 — Event-driven

When `voice_eval._linters()` builds the linter battery, the returned dict shall
include `shape_variance` keyed to `lint_shape_variance` and `aphorism_density` keyed
to `lint_aphorism_density`; both shall be reported in the standard per-1000-word
linter densities table.

## ADD REQ-VOICE-026 — Event-driven

When the liveness contract test in `tests/test_system_prompt_liveness.py` runs, for
each mode in `VALID_MODES` it shall additionally assert that the mode prompt
contains the self-turning mandate phrase.

## ADD REQ-VOICE-027 — Ubiquitous

The change shall leave `system_prompt_loader.py`, `VALID_MODES`, `DEFAULT_MODE`,
`assets/russell-corpus/index.json`, `references/russell-corpus-map.md`,
`assets/longfellow-corpus/index.json`, the Russell-Delta scorer, the liveness
composite formula in `scripts/liveness.py`, `lint_ornament`, `lint_burstiness`,
`lint_paragraph_motion`, `lint_concrete_instance_density`, all other existing
linters, and the reading-council scripts unmodified. The liveness composite shall
not be extended to include the two new signals; they shall report alongside, not
inside.
