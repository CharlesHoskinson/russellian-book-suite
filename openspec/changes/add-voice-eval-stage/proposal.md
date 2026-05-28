# Add a voice-eval generate-and-compare stage

## Why

We have manually generated Russell-voice prose and compared it to the genuine article
with the Russell-Delta scorer and the linter battery. This change makes that a
repeatable, committed stage: generate N paragraphs under a mode contract and compare
them to original Russell.

## What changes

- `skills/russellian-style/scripts/voice_eval.py`:
  - `generate_paragraphs(topic, mode, n, llm_call)` — builds the generation prompt from
    the mode contract and calls an injected LLM callable.
  - `evaluate(generated_text, russell_baseline_text=None)` — scores generated prose with
    the Russell-Delta scorer and the 12 linters; optional side-by-side against a real
    Russell baseline.
  - `run(...)`, `write_report(...)`, and a CLI.
- Tests with a fake LLM callable (no live calls, no network).
- A demo bundle under `docs/audits/2026-05-27-voice-eval/` (30 paragraphs + comparison).
- Register the `VOICE-EVAL` capability slug in `openspec/README.md`.

## What does not change

The stage is advisory: it gates nothing. It makes no live LLM calls (the LLM is an
injected callable) and no network calls. The Russell-Delta scorer, linters, prompts, and
profile are reused unchanged.

## Design

See `docs/specs/2026-05-27-voice-eval-stage-design.md`.
