# Guard the russellian voice against template fatigue (revised after QA pass)

## Why

The Longfellow-liveness blend solved the decoration fault diagnosed in the v1 snails
essay. A v3 snails essay produced by the new voice then received its own reader's
verdict: *one move at sixteen-time density* (fact → pivot → aphorism about humanity),
ear learns the meter by paragraph four, persona too pleased with itself,
Edwardian-familiar-essay pastiche. The reading council scored v3 4/4/4/4 — the suite
cannot see what the reader saw.

A five-agent QA pass on the first draft of this change surfaced a paradigmatic
finding: **the deterministic-linter strategy has hit its limit.** Each iteration
ships a regex to catch the named fault; the next reader names the fault one
abstraction layer up; regex is perpetually behind. The fix is to put a
reader-equivalent at the top of the stack — an LLM-judge step — alongside two
rebuilt deterministic linters that correct the failure modes the QA pass identified
in the first draft.

## What changes

- **Add `scripts/chassis_judge.py`** — the LLM-judge step. Single LLM call per essay,
  caller-provided dispatcher (no live calls in tests; mirrors
  `reading_scores.run_reading_council`). Extracts per-paragraph rhetorical moves,
  induces a move taxonomy, reports most-frequent-move frequency, and emits a
  one-sentence "unsympathetic critique." Advisory. The escape from the deterministic-
  instrument treadmill.
- **Add `scripts/lint_chassis_uniformity.py`** — rebuilt from the first draft's
  `lint_shape_variance`. Combines four signals (marker-hit shape dominance over a
  3-of-5 window; consecutive-shape streak; paragraph-shape-sequence Shannon entropy
  below threshold; humanity-token closer-density concentration). The marker-hit
  requirement excludes the `assertion_justification` fallback that produced
  false-positive saturation in the first draft; the closer-density signal catches
  chassis monotony when surface shapes are varied. Pure stdlib; advisory.
- **Add `scripts/lint_humanity_token_closers.py`** — rebuilt from the first draft's
  `lint_aphorism_density` and renamed honestly. Word cap raised from 18 to 28 (Russell's
  characteristic closers run 20–30 words); broadened humanity tokens (adds `men`, `man`,
  `nature`, `each of us`, `no one`, `anyone`, `everyone`, `the modern world`);
  first-person-singular subtraction (genuine aphorisms aren't testimony); concrete-
  instance-marker disqualifier preserved. Pure stdlib regex; advisory.
- **Promote `_strip_quotes` to public `strip_quotes`** in `lint_ornament.py` (one-line
  rename) so the new closer-density linter can cross-import it cleanly, matching the
  existing `from scripts.lint_paragraph_motion import classify_paragraph` idiom.
- **Wire the two new linters into `voice_eval._linters()`** so they appear in the
  standard density table. The chassis-judge is **not** auto-wired into `voice_eval`
  (it requires a dispatcher; kept separate, matching `reading_scores`).
- **Two new donor entries in `longfellow-liveness-map.md`'s "Disciplined-lyricism
  prose models"**: **Joan Didion** (with the corrected 5-technique entry —
  aphorism-as-target, catalogue-as-withheld-verdict, landscape-as-pre-argument,
  fragmentary-form-as-argument, physical-circumstance-as-epistemic-condition; failure
  modes; citation-backed sources) and **John McPhee** (technical-essay register,
  process-as-argument, long-sentence-as-verbed-noun-chain, named-expert-as-locus,
  structural-conceit-from-subject). Two post-1950 donors shift real corpus weight off
  the Edwardian-familiar-essay register.
- **Add tests** for all three new instruments (`test_chassis_uniformity.py`,
  `test_humanity_token_closers.py`, `test_chassis_judge.py`), each with
  `pytestmark = pytest.mark.windows_canary`, none named `test_lint_*` so the
  conftest's spaCy-absent skip glob doesn't catch them.
- **Add a validation bundle** at `docs/audits/2026-05-28-snails-v3-vs-v3.1/`: snails-
  v3.1 (rewritten + Lippinus/Bernoulli-mason fixes), `chassis-judge.json` (LLM-judge
  on both essays), deterministic telemetry, reading-council comparison, README with
  the two **preregistered falsification conditions**:
  1. `chassis_judge.most_frequent_move_frequency` ≥ 0.50 in v3.1 → design fails.
  2. `chassis_judge.unsympathetic_critique` for v3.1 contains chassis/template/
     metronome/etc. → design fails regardless of linter numbers.

## What does NOT change (vs. the first draft of this spec)

- **The self-turning paragraph mandate is dropped.** Self-contradictory by
  construction; the donor expansion + LLM-judge carry the counter-monotony load.
- **No new capability slug.** Extend `VOICE`; the prior iteration's principle holds.
- **The liveness composite is not extended.** The new signals report alongside, not
  inside.
- **No gate added.** All new instruments advisory.

## What does NOT change (vs. main)

`system_prompt_loader.py`, `VALID_MODES`, `DEFAULT_MODE`, the Russell corpus index
and map, the Longfellow corpus index, the Russell-Delta scorer, every existing
linter (`ornament`, `burstiness`, `paragraph_motion`, `concrete_instance_density`,
`hedges`, `passive_voice`, etc.), the reading-council scoring scripts, and the
existing `## Liveness` subsections of the three mode prompts are all unmodified.
`lint_ornament.py` receives only the one-line public rename of `_strip_quotes` →
`strip_quotes`; no behaviour change.

## Design

See `docs/specs/2026-05-28-voice-anti-monotony-design.md`.

## Branch base

`feat/voice-anti-monotony` is based on `feat/longfellow-liveness` (the new change
extends files added there: the `longfellow-liveness-map.md` reference). PR base at
finish time: `feat/longfellow-liveness` (stacked PR) until that branch merges to
main, then rebase onto main. If the parent receives review feedback altering the
`longfellow-liveness-map.md` prose-models section, the donor additions reapply by
hand.
