# Design — voice calibration prompts

Full design: `docs/specs/2026-05-27-russellian-voice-calibration-design.md`.

## Technical approach

Inline per-mode sections, no loader change (approach A of three considered; B was
loader-assembled shared block, C was corpus-driven assembly at load time). Each mode
file gets an appended `# Calibration and planning` section. The loader stays trivial,
each file stays self-contained, and the change is additive.

## Key decisions

- Planning is silent: mapped before drafting, never emitted into the manuscript. These
  are composition prompts, not chat; a visible thinking block would leak into the book.
- Anchors cite existing corpus rows by ID; no new corpus entries, no schema coupling.
- Touchstone quotes are verified verbatim against the cited public-domain source before
  commit. Verified rows: `problems-010` (technical), `free-001` (polemic),
  `analysis-008` (narrative). Verbatim text and URLs live in the implementation plan.
- Duplication of the planning language across three files is deliberate and matches the
  files' existing shared structure.

## Test approach

`tests/test_system_prompt_calibration.py` asserts, per mode in `VALID_MODES`: the
section heading, the move vocabulary, and at least one attributed anchor. TDD: tests
first and failing, then add sections. `test_system_prompt_loader.py` is unaffected.

## Rejected alternatives

- B (loader assembles shared calibration block): changes the consumption path and adds
  code/test surface for a prose change.
- C (corpus-driven assembly from `index.json`): couples prompt assembly to the corpus
  schema; out of scope while corpus stays untouched. Revisit at ~500 entries.
