# Russellian voice calibration for mode system prompts

Date: 2026-05-27
Status: proposed
Capability: russellian-voice (`VOICE`)

## Problem

The three mode system prompts at `skills/russellian-style/assets/system-prompts/`
(`technical-exposition.md`, `narrative-editorial.md`, `polemic.md`) are loaded
verbatim into the composition stage by `system_prompt_loader.load(mode)`. They are
sharp on negative constraints and structural mandates, but they omit two things that
the corpus discipline already names as the real target:

1. No reference to the corpus's rhetorical-move vocabulary. `russell-corpus-map.md`
   names the point as "paragraph motion: concession, example, distinction,
   consequence, and turn," yet none of the three prompts asks the drafter to plan that
   motion.
2. No exemplar anchors. The 50-paragraph corpus exists as pointers, and the map says
   not to inline full passages, so the prompts carry no calibration touchstone at all.

A third, smaller gap: dry-understatement guidance exists only in `polemic.md`
("dry irony"); `technical-exposition.md` and `narrative-editorial.md` have none.

This is not a claim that a better prompt is the lever. The suite's position stands:
the gates enforce the contract. This change sharpens the *input* to composition so the
downstream linters and personas receive better raw material; it adds no gate and
weakens none.

## Scope

In scope: the three mode prompt files, a content-contract test, and a validation
bundle. Out of scope and explicitly untouched: `system_prompt_loader.py`,
`VALID_MODES`, `DEFAULT_MODE`, `assets/russell-corpus/index.json`,
`references/russell-corpus-map.md`, and every linter and audit script. Corpus growth
stays a separate concern with its own tool (`tools/build-russell-corpus`).

## Design

Each mode file gains one appended section, `# Calibration and planning`, holding
four parts.

### a. Silent planning directive

Before drafting, the drafter privately maps the paragraph's motion using the move
vocabulary (`concession → example → distinction → consequence → turn`) and decides
where the turn lands. The plan is never emitted; only the prose ships. These are
book-composition prompts, so the planning step must not surface as a visible block in
the manuscript.

### b. Mode-matched move anchors

A short list of *rhetorical-move → calibration-lesson* lines lifted from
`russell-corpus-map.md`, filtered per mode:

- `technical-exposition` — `problems`, `external-world`, `analysis-mind`
  (define abstractions through ordinary cases; counterexample before conclusion;
  classify before evaluating; end on a reversal that changes valuation).
- `polemic` — `free-thought`, `political-ideals`
  (antithesis around a memorable reversal; personify the opposing view; ground the
  argument in a named official or date; state both sides of a principle in one
  paragraph).
- `narrative-editorial` — the concrete-instance and vivid-empirical rows
  (`analysis-008`, `problems-007`), since the corpus has no pure-scene mode; these are
  its most scene-adjacent anchors.

Anchors cite existing corpus rows by ID. No new corpus entries are created.

### c. One contrastive touchstone per mode

A flat-AI sentence (written for the prompt) paired with a short (≤2 sentences)
public-domain Russell quote that demonstrates the target motion and wit. The quote
carries source attribution (the corpus source ID and URL). The touchstone teaches
motion and register, not diction to copy.

Quotes are verified verbatim against the cited public-domain source before use; no
quote is treated as verbatim until checked. The selected touchstones, verified during
planning: technical → `problems-010` (Problems of Philosophy, uncertainty turned into
value); polemic → `free-001` (Free Thought and Official Propaganda, the will-to-doubt
antithesis — selected over the earlier `free-006` candidate, which proved a weaker
fit); narrative → `analysis-008` (The Analysis of Mind, the hungry-cat learning
sequence). Verbatim text and source URLs live in the implementation plan.

### d. Understatement line

`technical-exposition.md` and `narrative-editorial.md` each gain one directive on
Russell's dry understatement: let an absurd view show through precise statement, not
exclamation. `polemic.md` already covers this.

## Placement

The new section is appended at the end of each file so the existing `# Role`,
structural mandates, and negative constraints remain primary. The three files keep
their self-contained form; the planning language is repeated (tailored) per file,
consistent with the structure they already share.

## Fit with the gate architecture

The calibration block reinforces the linters and contradicts none:

- motion planning and varied cadence ↔ `lint_sentence_rhythm`
- "earn the list before naming it" ↔ `lint_listicle_abstract`
- understatement over exclamation ↔ `lint_signal_density`

No linter, threshold, or schema changes.

## Testing

New `tests/test_system_prompt_calibration.py`. For each mode in `VALID_MODES`, assert
the loaded prompt contains:

- the `# Calibration and planning` heading,
- the move-vocabulary string (`concession`, `consequence`, `turn`),
- at least one attributed anchor (a source-ID or URL token adjacent to a quote).

Tests are written first and fail (no section yet), then the sections are added and the
tests pass. The existing `test_system_prompt_loader.py` stays green; it monkeypatches
`PROMPTS_DIR` and does not assert on the real files. Each verbatim quote is verified
against its cited source before commit.

## Validation

Draft a 600-word essay, "On the Absurdities of Artificial Intelligences Governing
Human Passions," under the revised `polemic` prompt (argued title → polemic mode).
Run the existing `russellian-style` linters and `russellian-style-audit` against it and
require no new defects versus a baseline essay drafted under the pre-change prompt.
The essay, both lint reports, and a short readme go under
`docs/audits/2026-05-27-russellian-voice-calibration/`, matching the existing
audit-bundle pattern.

## Out of scope / follow-ups

- Corpus-driven prompt assembly (render anchors from `index.json` at load time). Worth
  doing once the corpus reaches ~500 entries; tracked as a follow-up.
- Corpus expansion itself, via `tools/build-russell-corpus`.
