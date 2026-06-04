# Design — voice-eval stage

Full design: `docs/specs/2026-05-27-voice-eval-stage-design.md`.

## Technical approach

A cohesive `voice_eval.py` inside `russellian-style/scripts/` that reuses the skill's own
`system_prompt_loader`, `score_russell_delta`, and linter modules. Generation is an
injected `Callable[[str], str]` (suite convention); scoring is deterministic and offline.
"Compare to original Russell" = the Russell-Delta verdict against the corpus band, plus
the 12-linter battery on the generated prose and (optionally) a side-by-side real Russell
baseline.

## Key decisions

- Lives in `russellian-style/scripts/` (not a separate `tools/` project): it is tightly
  coupled to the skill's prompts, scorer, and linters.
- LLM is injected; no live LLM calls, none in tests. Operator/foreground session supplies
  the callable at runtime.
- Russell linter baseline is operator-supplied and optional; the Delta verdict is the
  always-on comparison to original Russell.
- Default N = 30 paragraphs; default mode = technical-exposition.
- Advisory only; gates nothing.

## Rejected alternatives

- Bolt the eval into `book-compose`'s chapter pipeline: overkill for a focused stage.
- Standalone `tools/` project with its own venv: more scaffolding for code tightly
  coupled to russellian-style internals.

## Test approach

`generate_paragraphs` tested with a fake llm_call (prompt content + return passthrough,
no spaCy). `evaluate` tested on short fixture prose for report structure (Delta + linter
blocks; runs the real linters, needs the spaCy venv like existing report tests).
Determinism and advisory-only asserted. No network, no live LLM.
