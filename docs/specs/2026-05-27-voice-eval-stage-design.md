# Voice-eval generate-and-compare stage

Date: 2026-05-27
Status: proposed
Capability: voice-eval (`VOICE-EVAL`)

## Problem

We have, by hand, generated prose in Russell's voice and compared it to the genuine
article using the Russell-Delta scorer and the linter battery. Nothing in the suite
does this as a repeatable, committed stage. This change adds one: generate N paragraphs
under a mode contract and compare them to original Russell.

## Scope

In scope: a `voice_eval.py` orchestration in `russellian-style/scripts/` (generation
via an injected LLM callable, scoring via the Russell-Delta scorer and the 12 linters,
a comparison report), a CLI, a markdown report writer, tests, and a demo bundle.

Out of scope (explicit follow-ups): contrastive Delta (Russell vs. other authors),
budget-linter recalibration, the LLM rubric "virtues" judge.

## Design

### Component

`skills/russellian-style/scripts/voice_eval.py`, three focused functions plus a CLI:

- `generate_paragraphs(topic, mode, n, llm_call) -> str` — loads the mode contract with
  `system_prompt_loader.load(mode)`, builds a generation prompt embedding the contract,
  the topic, and the requested paragraph count, calls `llm_call(prompt)`, and returns
  the prose. `llm_call: Callable[[str], str]` is injected.
- `evaluate(generated_text, russell_baseline_text=None) -> dict` — scores the generated
  prose with `score_russell_delta.score` (delta, verdict, band) against the committed
  profile, and runs the full russellian-style linter battery (per-linter counts plus
  per-1000-word densities). If a baseline is given, scores it the same way and reports
  generated-vs-baseline side by side.
- `run(topic, mode, n, llm_call, russell_baseline_path=None) -> dict` — orchestrates
  generate then evaluate; returns the report dict.
- `write_report(report, out_path)` — renders the markdown bundle.

### LLM injection

Generation takes the LLM as a `Callable[[str], str]`, the suite's convention. The stage
makes no live LLM calls; tests pass a fake callable returning fixture prose. At runtime
the operator (or a foreground Claude session) supplies the callable. There is no live
LLM in tests.

### Comparison signals

"Compare to original Russell" uses two signals:

1. Russell-Delta: the verdict places the generated prose against Russell's own band
   (`within` / `at the edge of` / `outside Russell's range`). This is the always-on
   comparison and needs no stored prose.
2. The 12-linter battery on the generated prose; and, when an operator supplies a real
   Russell excerpt (`--russell-baseline <path>`, default none), the same battery on the
   baseline for a side-by-side density table.

### Output

`run` returns a dict; `write_report` renders a markdown bundle under
`docs/audits/2026-05-27-voice-eval/` containing the generated paragraphs and a
comparison table (Delta/verdict, per-linter densities, generated vs. baseline).

### Defaults

Paragraph count defaults to 30. Mode defaults to `technical-exposition`.

## Testing

- `generate_paragraphs` with a fake `llm_call`: assert the prompt passed to the callable
  contains the mode contract text, the topic, and the paragraph count; assert the return
  is the callable's output. No spaCy, no network.
- `evaluate` on short fixture prose: assert the report contains a `russell_delta` block
  (metric, delta, verdict) and a `linters` block with per-linter counts; with a baseline,
  assert a `baseline` block and side-by-side deltas. (Runs the real linters; needs the
  spaCy venv, as the existing report tests do.)
- Determinism: same inputs produce the same report (modulo the injected llm_call).
- Advisory: no code path raises or gates on the scores.

## Demo / validation

Run the stage with a live generator (a foreground Claude session acting as `llm_call`)
to produce 30 paragraphs on a chosen topic, compare against a genuine Russell excerpt,
and commit the bundle under `docs/audits/2026-05-27-voice-eval/`.

## Consistency with the suite

The stage reuses `system_prompt_loader`, `score_russell_delta`, and the linters; it adds
no gate (advisory); it follows the injected-LLM-callable convention; scoring is
deterministic and offline.
