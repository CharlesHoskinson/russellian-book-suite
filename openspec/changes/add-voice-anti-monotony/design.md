# Design — add-voice-anti-monotony

Full design: `docs/specs/2026-05-28-voice-anti-monotony-design.md`. This file records
the technical approach and the decisions that shaped the spec deltas.

## Approach

Extend the existing `VOICE` capability with two new advisory linters, a prompt-level
mandate, and one donor addition. No new capability slug. The two halves of the fix:

- **Detect** the chassis fault deterministically: paragraph-shape variance + aphorism
  density, both stdlib regex, both quote-excluding, both advisory. Each new linter is
  computable without spaCy and CI-safe.
- **Counter** the chassis fault in the writer: a self-turning paragraph mandate in
  each mode's `## Liveness` subsection, plus a contemporary anti-aphoristic donor
  (Joan Didion) added to the liveness map.

## Key decisions

- **Reuse `classify_paragraph` from `lint_paragraph_motion`.** Stdlib, already used by
  `voice_eval._motion_variety`. No new shape classifier; no new vocabulary.
- **Per-instance findings.** Both new linters return one dict per match (one per
  offending run, one per qualifying closer), so `voice_eval._signals`'s
  `len(fn(path)) / n_words * 1000` produces a meaningful per-1000-word density. Same
  contract as `lint_hedges` and the re-shaped `lint_ornament`.
- **Concrete-instance guard on aphorism closers.** A closer that names a proper noun,
  year, or numeric quantity is grounded, not aphoristic. This avoids flagging
  Russell's own grounded closers ("Russell's table in this room earns the
  abstraction") while catching the ungrounded verdict-shaped sentence the chassis
  produces.
- **Identical self-turning mandate across modes.** The mandate is structural; it does
  not scale with the per-mode intensity dial. Every essay needs at least one paragraph
  that refuses the running thesis, regardless of mode.
- **The new signals report alongside the liveness composite, not inside it.** The
  composite already saturates (the prior audit documented the cadence ceiling and the
  concreteness gap). Adding more terms would worsen saturation; the new advisory
  numbers stand on their own.
- **Didion referenced by technique, never quoted.** Post-1950, in copyright. Same
  pattern as Carson/Dillard/Eiseley.

## CI constraint

Both new linters are stdlib + `re` only. Test files `test_shape_variance.py` and
`test_aphorism_density.py` are named without the `test_lint_` prefix so the russellian-
style conftest's spaCy-absent `collect_ignore_glob` does not silently skip them on CI
legs without the spaCy English model.

## Rejected

A new `voice-anti-monotony` capability (extend `VOICE`); promoting either linter to a
hard gate (advisory in v1 per convention); aphorism detection via LLM judge (regex is
YAGNI-correct for a v1 advisory); multiple post-1950 donors in one change (Didion
alone is the user's pick); folding the new signals into the liveness composite (would
worsen the documented saturation).
