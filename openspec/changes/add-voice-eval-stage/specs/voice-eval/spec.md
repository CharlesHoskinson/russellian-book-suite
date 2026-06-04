# Spec delta — voice-eval

Capability: `VOICE-EVAL` (voice-eval)
Delta against `openspec/specs/voice-eval/spec.md` (new capability; all ADD).

## ADD REQ-VEVAL-001 — Event-driven

When `generate_paragraphs` runs with a mode, topic, paragraph count, and an LLM callable,
it shall load the mode contract via `system_prompt_loader`, build a generation prompt
embedding the contract, the topic, and the requested paragraph count, and return the
callable's output.

## ADD REQ-VEVAL-002 — Ubiquitous

The stage shall accept the LLM as an injected `Callable[[str], str]`; it shall make no
live LLM calls of its own, and tests shall make no live LLM calls.

## ADD REQ-VEVAL-003 — Event-driven

When `evaluate` runs on generated text, it shall report the Russell-Delta (delta,
verdict, band) computed against the committed profile and the full russellian-style
linter battery (per-linter counts and per-1000-word densities).

## ADD REQ-VEVAL-004 — Optional feature

Where a real Russell baseline text is supplied, `evaluate` shall score it with the same
signals and report the generated prose and the baseline side by side.

## ADD REQ-VEVAL-005 — Ubiquitous

Given fixed inputs (including a fixed LLM callable output), the stage's scoring shall be
deterministic, and the stage shall require no network access.

## ADD REQ-VEVAL-006 — Ubiquitous

The stage shall be advisory: it shall not gate, fail, or block any pipeline.

## ADD REQ-VEVAL-007 — Event-driven

When `run` produces a report, the report writer shall emit a markdown bundle containing
the generated paragraphs and the comparison table.

## ADD REQ-VEVAL-008 — Ubiquitous

The default paragraph count shall be 30.
