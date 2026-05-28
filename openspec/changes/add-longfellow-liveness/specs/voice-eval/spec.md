# Spec delta — voice-eval

Capability: `VOICE-EVAL` (voice-eval)
Delta against the `voice-eval` capability as established by `add-voice-eval-stage`
(REQ-VEVAL-001..008; not yet archived to `openspec/specs/`). All ADD; numbering continues
at 009; no renumbering.

## ADD REQ-VEVAL-009 — Event-driven

When `evaluate` runs on text, it shall compute an order-sensitive cadence signal — the
normalized pairwise variability index (nPVI) of sentence lengths in words — using the
standard library only, importing nothing from `lint_common`, and excluding sentences below
a fixed word floor so that short fragments cannot inflate the signal.

## ADD REQ-VEVAL-010 — Event-driven

When `evaluate` runs on text, it shall report a liveness summary composed from existing
instruments — paragraph-motion variety, concrete-instance density, and the nPVI cadence
signal — reduced by an ornament penalty derived from `lint_ornament`; it shall introduce no
re-implementation of burstiness or concrete-instance density.

## ADD REQ-VEVAL-011 — Optional feature

Where a baseline text is supplied, `evaluate` shall report the liveness summary for the
generated prose and the baseline side by side, so the before/after difference is visible.

## ADD REQ-VEVAL-012 — Unwanted behaviour

If the liveness summary is reported, then it shall be presented as descriptive telemetry;
the stage shall make no claim that a generation "beats", "passes", or is "more alive than"
the Russell baseline. Qualitative judgement of improvement is delegated to the
reading-council before/after audit.

## ADD REQ-VEVAL-013 — Ubiquitous

Given fixed inputs, the cadence signal and liveness summary shall be deterministic and
shall require no network access.

## ADD REQ-VEVAL-014 — Ubiquitous

The new signals shall be advisory: they shall not gate, fail, or block any pipeline.
