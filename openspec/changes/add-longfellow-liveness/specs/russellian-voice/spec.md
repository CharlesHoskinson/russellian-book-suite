# Spec delta — russellian-voice

Capability: `VOICE` (russellian-voice)
Delta against the `russellian-voice` capability as established by
`add-voice-calibration-prompts` (REQ-VOICE-001..007; not yet archived to
`openspec/specs/`). All ADD; numbering continues at 008; no renumbering.

## ADD REQ-VOICE-008 — Ubiquitous

Each mode system prompt under `skills/russellian-style/assets/system-prompts/` shall
contain a `## Liveness` subsection within its `# Calibration and planning` section.

## ADD REQ-VOICE-009 — Ubiquitous

Each `## Liveness` subsection shall specify drive-oriented craft directives —
sentence-length percussion, base-clause-first cumulative construction,
knot-and-resolution cadence, anaphora tied to the argued term, and one concrete anchor per
abstraction — and shall express its intensity by what each level permits and excludes, not
by adjective alone.

## ADD REQ-VOICE-010 — Ubiquitous

The liveness intensity shall be set per mode: `technical-exposition` low,
`narrative-editorial` high, `polemic` medium; each prompt shall state its own level.

## ADD REQ-VOICE-011 — Ubiquitous

Each `## Liveness` subsection shall present at least one liveness anchor pairing a flat
sentence with a livelier rendering, and shall state the firewall: borrow cadence and
image-logic only, never meter, rhyme, archaism, or sentiment.

## ADD REQ-VOICE-012 — Unwanted behaviour

If a prompt reproduces a donor passage verbatim, then the passage shall be public-domain
Longfellow, quoted exactly and attributed to a `longfellow-corpus` snippet ID; in-copyright
prose models (Carson, Dillard, Eiseley) shall be referenced by named technique only and
never quoted.

## ADD REQ-VOICE-013 — Ubiquitous

The skill shall provide a deterministic ornament linter (`scripts/lint_ornament.py`) that
flags purple-prose markers — adjective stacking, an adverb amplifying an already-strong
verb, abstract emotion words applied without a concrete vehicle, apostrophe, archaic
diction tokens, and nature-mirrors-mood clauses — and that excludes quoted spans from
analysis.

## ADD REQ-VOICE-014 — Unwanted behaviour

If the ornament linter is imported, then it shall import no spaCy and nothing from
`lint_common`; it shall load and run under the CI `[ci]` extra without the spaCy model.

## ADD REQ-VOICE-015 — Ubiquitous

The ornament linter shall be advisory: it shall not gate, fail, or block any pipeline, and
shall record an internal tier for the report only.

## ADD REQ-VOICE-016 — Ubiquitous

The change shall leave `system_prompt_loader.py`, `VALID_MODES`, `DEFAULT_MODE`,
`assets/russell-corpus/index.json`, `references/russell-corpus-map.md`, and the
Russell-Delta scorer unmodified.

## ADD REQ-VOICE-017 — Event-driven

When the liveness test suite runs, for each mode in `VALID_MODES` it shall assert the
presence of the `## Liveness` subsection, the mode's declared intensity level, and at least
one anchor carrying the firewall statement.
