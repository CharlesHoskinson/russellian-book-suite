# Tasks — add-voice-anti-monotony

Each line cites the REQ IDs it satisfies. Implementation plan to be produced by
`superpowers:writing-plans` from this change's `docs/specs/2026-05-28-voice-anti-monotony-design.md`.

1. **Public `strip_quotes` rename** (`scripts/lint_ornament.py`,
   `tests/test_ornament.py`) — REQ-VOICE-026. One-line rename of `_strip_quotes` to
   `strip_quotes`; update internal call sites; preserve behaviour. Tests must still
   pass.
2. **`lint_chassis_uniformity`** (`scripts/lint_chassis_uniformity.py`,
   `tests/test_chassis_uniformity.py`) — REQ-VOICE-018, REQ-VOICE-019. Four-signal
   linter; reuses `classify_paragraph` and (after Task 3)
   `lint_humanity_token_closers` for the closer-density signal. Test file name
   `test_chassis_uniformity.py` (NOT `test_lint_*`) with `windows_canary` marker.
3. **`lint_humanity_token_closers`** (`scripts/lint_humanity_token_closers.py`,
   `tests/test_humanity_token_closers.py`) — REQ-VOICE-020, REQ-VOICE-021. Five-gate
   regex linter; cross-imports `strip_quotes` from Task 1. Test file name not
   `test_lint_*`; `windows_canary` marker. Fixtures must include the v1 snails
   closers the first-draft regex missed.
4. **`chassis_judge`** (`scripts/chassis_judge.py`,
   `tests/test_chassis_judge.py`) — REQ-VOICE-022, REQ-VOICE-023. Single LLM call
   via caller-provided dispatcher; pure-function prompt builder + response parser
   unit-tested without a live LLM.
5. **`voice_eval` wiring** (`scripts/voice_eval.py`,
   `tests/test_voice_eval.py`) — REQ-VOICE-024. Two new entries in `_linters()`:
   `chassis_uniformity` and `humanity_token_closers`. The chassis-judge stays out of
   `voice_eval`; it is invoked separately.
6. **Donor expansion in the liveness map** (`references/longfellow-liveness-map.md`)
   — REQ-VOICE-025. Replace the first-draft Didion bullet with the corrected
   5-technique entry; add the McPhee entry; both referenced by named technique only,
   never quoted.
7. **Validation audit bundle**
   (`docs/audits/2026-05-28-snails-v3-vs-v3.1/`) — REQ-VOICE-027. snails-v3.1 essay
   (rewritten + Lippinus + Bernoulli-mason fixes); deterministic telemetry; the
   chassis-judge run on both v3 and v3.1; reading-council comparison; README
   stating both preregistered falsification conditions and recording the outcome
   honestly (including in the failure case).

Out of scope, asserted unchanged by REQ-VOICE-028: `system_prompt_loader.py`,
`VALID_MODES`, `DEFAULT_MODE`, the russell-corpus and longfellow-corpus index files,
the russell-corpus-map, the three mode prompts and their `## Liveness` subsections,
`test_system_prompt_liveness.py`, the Russell-Delta scorer, the liveness composite,
all existing linters (only `lint_ornament` receives the rename in Task 1; behaviour
unchanged), the reading-council scripts.
