# Tasks — add-longfellow-liveness

Each line cites the REQ IDs it satisfies. Implementation plan:
`docs/plans/2026-05-28-longfellow-liveness.md`.

1. **nPVI cadence signal** (`scripts/liveness.py:npvi`, `tests/test_liveness.py`) — REQ-VEVAL-009, REQ-VEVAL-013.
2. **Liveness composite** (`scripts/liveness.py:liveness_summary`, `tests/test_liveness.py`) — REQ-VEVAL-010, REQ-VEVAL-013, REQ-VEVAL-014.
3. **Ornament linter** (`scripts/lint_ornament.py`, `tests/test_ornament.py`, `SKILL.md`) — REQ-VOICE-013, REQ-VOICE-014, REQ-VOICE-015.
4. **voice_eval wiring** (`scripts/voice_eval.py`, `tests/test_voice_eval.py`) — REQ-VEVAL-009, REQ-VEVAL-010, REQ-VEVAL-011, REQ-VEVAL-012, REQ-VEVAL-013, REQ-VEVAL-014.
5. **Longfellow corpus + builder** (`tools/build-longfellow-corpus/`, `assets/longfellow-corpus/index.json`) — REQ-VOICE-012.
6. **Liveness map** (`references/longfellow-liveness-map.md`) — REQ-VOICE-009, REQ-VOICE-011, REQ-VOICE-012.
7. **Per-mode `## Liveness` + contract test** (`assets/system-prompts/*.md`, `tests/test_system_prompt_liveness.py`) — REQ-VOICE-008, REQ-VOICE-009, REQ-VOICE-010, REQ-VOICE-011, REQ-VOICE-012, REQ-VOICE-017.
8. **Validation audit bundle** (`docs/audits/2026-05-27-longfellow-liveness-before-after/`) — validates the change against the success gate (reading-council A/B).

Out of scope, asserted unchanged by REQ-VOICE-016: `system_prompt_loader.py`,
`VALID_MODES`, `DEFAULT_MODE`, `assets/russell-corpus/index.json`,
`references/russell-corpus-map.md`, the Russell-Delta scorer.
