# Spec delta — russellian-voice (revised after QA pass)

Capability: `VOICE` (russellian-voice)
Delta against the `russellian-voice` capability as established by
`add-voice-calibration-prompts` (REQ-VOICE-001..007) and extended by
`add-longfellow-liveness` (REQ-VOICE-008..017); none yet archived to
`openspec/specs/`. All ADD; numbering continues at 018; no renumbering.

## ADD REQ-VOICE-018 — Event-driven

When `lint_chassis_uniformity` runs on a markdown document, it shall split the
document into paragraphs, classify each via `lint_paragraph_motion.classify_paragraph`,
and emit one or more findings drawn from four independent signals: (a) a marker-hit
shape-dominance check that ignores paragraphs classified into the
`assertion_justification` fallback and flags any single marker-hit shape occupying
at least three of any five consecutive paragraphs; (b) a streak check that flags any
run of at least three consecutive paragraphs sharing a shape (including the
fallback); (c) a paragraph-shape-sequence Shannon-entropy check that emits one
document-level finding if entropy is below 1.5 bits over the 7-shape taxonomy;
(d) a closer-density check that emits one document-level finding when at least 50%
of paragraphs in a document of at least 8 paragraphs have a humanity-token closer
(reusing `lint_humanity_token_closers`'s gate).

## ADD REQ-VOICE-019 — Ubiquitous

`scripts/lint_chassis_uniformity.py` shall import nothing from
`scripts.lint_common`, shall import no spaCy, and shall use only the standard
library and `re`; it shall load and run under the CI `[ci]` extra without the spaCy
English model. It shall be advisory: it shall not gate, fail, or block any pipeline,
and shall record an internal tier for the report only.

## ADD REQ-VOICE-020 — Event-driven

When `lint_humanity_token_closers` runs on a markdown document, it shall apply a
quote-exclusion pass (using `strip_quotes` from `lint_ornament`) and, for each
paragraph, test the paragraph's closing sentence against five gates: (a) between 6
and 28 words inclusive; (b) contains at least one humanity-generalising token from
the closed list `we, our, us, ourselves, mankind, humanity, civilisation, modern life,
most people, most of us, the rest of us, none of us, men, man, nature, the modern
world, each of us, no one, anyone, everyone`; (c) contains no concrete-instance
marker (a capitalised non-initial word, a four-digit year, or a numeric quantity);
(d) contains no first-person-singular token (`\bI\b` or `\bmy\b`). It shall emit one
finding per qualifying closer.

## ADD REQ-VOICE-021 — Ubiquitous

`scripts/lint_humanity_token_closers.py` shall import nothing from
`scripts.lint_common`, shall import no spaCy, and shall use only the standard
library and `re` (it may import `strip_quotes` from `scripts.lint_ornament`); it
shall load and run under the CI `[ci]` extra without the spaCy English model. It
shall be advisory: it shall not gate, fail, or block any pipeline.

## ADD REQ-VOICE-022 — Event-driven

When `chassis_judge` runs on a document, it shall accept a single caller-provided
dispatcher of type `Callable[[str], str]`; it shall build a prompt that instructs an
LLM reader to label the rhetorical move executed in each paragraph, induce the move
taxonomy used, report the most-frequent move and its frequency, state whether the
essay can be summarised in a single move-shape, and write a one-sentence critique an
unsympathetic reader would write; it shall pass that prompt to the dispatcher exactly
once; and it shall return a dict containing the keys `metric` (set to
`"chassis-judge"`), `paragraph_moves` (list of strings), `move_taxonomy` (list of
unique strings), `most_frequent_move` (string), `most_frequent_move_frequency`
(float in 0..1), `single_move_summary` (bool), `unsympathetic_critique` (string),
and `advisory` (true).

## ADD REQ-VOICE-023 — Ubiquitous

`scripts/chassis_judge.py` shall make no live LLM calls of its own; the dispatcher
shall be the only side-effecting boundary. Tests for `chassis_judge` shall pass a
stubbed dispatcher and make no live LLM calls. The judge shall be advisory: it
shall not gate, fail, or block any pipeline.

## ADD REQ-VOICE-024 — Event-driven

When `voice_eval._linters()` builds the linter battery, the returned dict shall
include `chassis_uniformity` keyed to `lint_chassis_uniformity` and
`humanity_token_closers` keyed to `lint_humanity_token_closers`; both shall be
reported in the standard per-1000-word linter densities table. The chassis-judge
shall not be auto-wired into `voice_eval`; it shall remain a separately-invoked
module (matching the existing convention for `skills/review-conductor/scripts/reading_scores.py`).

## ADD REQ-VOICE-025 — Ubiquitous

The "Disciplined-lyricism prose models" section of
`references/longfellow-liveness-map.md` shall include an entry for **Joan Didion**
(referenced by named technique only, never quoted) describing five translatable
moves — the diagnostic aphorism that eats itself, the catalogue as withheld verdict,
the landscape that pre-argues, the fragmentary form as argument, the physical
circumstance as epistemic condition — plus failure modes and canonical texts and
critical sources; and an entry for **John McPhee** (referenced by named technique
only, never quoted) describing three translatable moves — the long sentence as a
chain of verbed nouns, the named expert as locus of the technical claim, the
structural conceit borrowed from the subject — plus failure modes and canonical
texts and critical sources.

## ADD REQ-VOICE-026 — Ubiquitous

In `scripts/lint_ornament.py`, the module-private `_strip_quotes` helper shall be
renamed to public `strip_quotes` (existing call sites within the module updated);
`scripts/lint_humanity_token_closers.py` shall cross-import `strip_quotes` from
`scripts.lint_ornament` rather than re-implement the helper. The behaviour of the
helper shall be unchanged by the rename.

## ADD REQ-VOICE-027 — Event-driven

When the validation audit for this change runs, it shall preregister two
falsification conditions before any v3.1 essay is written: (a) the audit shall fail
if `chassis_judge.most_frequent_move_frequency` for v3.1 is ≥ 0.50; (b) the audit
shall fail if `chassis_judge.unsympathetic_critique` for v3.1 contains any of the
substrings `"chassis"`, `"template"`, `"metronome"`, `"one move"`, `"same move"`,
`"every paragraph"`, or matches `r"\b(perform|performing)\b.{0,20}\b(wisdom|insight|moral)\b"`.
Either condition holding shall mean the design did not work, regardless of the
deterministic linter numbers.

## ADD REQ-VOICE-028 — Ubiquitous

The change shall leave `system_prompt_loader.py`, `VALID_MODES`, `DEFAULT_MODE`,
`assets/russell-corpus/index.json`, `references/russell-corpus-map.md`,
`assets/longfellow-corpus/index.json`, the three mode prompts under
`assets/system-prompts/`, the `## Liveness` subsections added by
`add-longfellow-liveness`, `tests/test_system_prompt_liveness.py`, the Russell-Delta
scorer, the liveness composite formula in `scripts/liveness.py`, `lint_ornament`'s
behaviour (only the `_strip_quotes` → `strip_quotes` rename is in scope),
`lint_burstiness`, `lint_paragraph_motion`, `lint_concrete_instance_density`, all
other existing linters, and the reading-council scripts unmodified. The liveness
composite shall not be extended to include the new signals; they shall report
alongside, not inside.
