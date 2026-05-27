# Spec delta — russellian-voice

Capability: `VOICE` (russellian-voice)
Delta against `openspec/specs/russellian-voice/spec.md` (new capability; all ADD).

## ADD REQ-VOICE-001 — Ubiquitous

Each mode system prompt under
`skills/russellian-style/assets/system-prompts/` shall contain a
`## Calibration and planning` section.

## ADD REQ-VOICE-002 — Event-driven

When a mode prompt is loaded for drafting, the prompt shall instruct the drafter to
map the paragraph's motion (concession, example, distinction, consequence, turn)
before writing, and shall instruct that this plan is not emitted into the manuscript.

## ADD REQ-VOICE-003 — Ubiquitous

Each mode prompt shall present at least two rhetorical-move anchors drawn from
`references/russell-corpus-map.md` and matched to that mode's rhetorical register.

## ADD REQ-VOICE-004 — Ubiquitous

Each mode prompt shall contain at least one contrastive touchstone pairing a flat
machine-prose sentence with a public-domain Russell passage of at most two sentences,
and the passage shall carry attribution to its corpus source ID.

## ADD REQ-VOICE-005 — Unwanted behaviour

If a mode prompt reproduces a Russell passage, then the passage shall be verbatim from
the cited public-domain source; paraphrase presented as quotation is forbidden.

## ADD REQ-VOICE-006 — Ubiquitous

The change shall leave `system_prompt_loader.py`, `VALID_MODES`, `DEFAULT_MODE`,
`assets/russell-corpus/index.json`, `references/russell-corpus-map.md`, and all linter
and audit scripts unmodified.

## ADD REQ-VOICE-007 — Event-driven

When the calibration test suite runs, for each mode in `VALID_MODES` it shall assert
the presence of the `## Calibration and planning` heading, the move vocabulary, and at
least one attributed anchor.
