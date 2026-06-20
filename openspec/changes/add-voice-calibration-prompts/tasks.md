# Tasks — voice calibration prompts

Lightweight checklist. The exhaustive TDD plan lives at
`docs/plans/2026-05-27-russellian-voice-calibration.md` (written via writing-plans).

- [ ] Add failing `tests/test_system_prompt_calibration.py` covering all modes
      (REQ-VOICE-001, REQ-VOICE-002, REQ-VOICE-003, REQ-VOICE-004, REQ-VOICE-007)
- [ ] Select and verify verbatim touchstone quotes against cited public-domain sources
      (REQ-VOICE-004, REQ-VOICE-005)
- [ ] Append `# Calibration and planning` to `technical-exposition.md`
      (REQ-VOICE-001..004 + understatement line)
- [ ] Append `# Calibration and planning` to `narrative-editorial.md`
      (REQ-VOICE-001..004 + understatement line)
- [ ] Append `# Calibration and planning` to `polemic.md` (REQ-VOICE-001..004)
- [ ] Confirm no edits to loader, corpus, or linters (REQ-VOICE-006)
- [ ] Run `russellian-style` test suite; confirm `test_system_prompt_loader.py` green
- [ ] Produce validation bundle under
      `docs/audits/2026-05-27-russellian-voice-calibration/` (essay + lint reports)
