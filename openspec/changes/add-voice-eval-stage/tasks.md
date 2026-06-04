# Tasks — voice-eval stage

Lightweight checklist. The exhaustive TDD plan lives at
`docs/plans/2026-05-27-voice-eval-stage.md` (written via writing-plans).

- [ ] `generate_paragraphs` TDD with a fake llm_call: prompt embeds mode contract +
      topic + count; returns callable output (REQ-VEVAL-001, REQ-VEVAL-002, REQ-VEVAL-008)
- [ ] `evaluate` TDD on fixture prose: Russell-Delta block + 12-linter block; optional
      baseline side-by-side (REQ-VEVAL-003, REQ-VEVAL-004)
- [ ] `run` + `write_report` (markdown bundle) + CLI (REQ-VEVAL-007)
- [ ] Confirm determinism + advisory-only (no gate/raise) (REQ-VEVAL-005, REQ-VEVAL-006)
- [ ] Run russellian-style suite; confirm no regressions
- [ ] Demo: a foreground session acts as llm_call to generate 30 paragraphs on a chosen
      topic; compare against a genuine Russell excerpt; commit bundle under
      `docs/audits/2026-05-27-voice-eval/`
