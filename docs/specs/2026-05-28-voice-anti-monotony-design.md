# Voice anti-monotony — design

Date: 2026-05-28
Status: approved direction; awaiting plan
Change: `openspec/changes/add-voice-anti-monotony/`
Base branch: `feat/longfellow-liveness` (depends on the per-mode `## Liveness`
sections, `longfellow-liveness-map.md`, and the `longfellow-corpus` index.json
from that change).

## Problem

The Longfellow-liveness blend solved the decoration fault (the v1 snails essay was
"more decorative than Russell"). A v3 snails essay produced by the new voice was then
read for its own faults, and the reader's verdict landed cleanly: the voice has *one
move and runs it sixteen times*. Every paragraph follows the same chassis — fact, pivot,
aphorism about humanity — and the reader's ear learns the meter by paragraph four. The
prose performs wisdom on a metronome. The persona is too pleased with itself. The
diction is Edwardian-familiar-essay pastiche (Eiseley by way of Chesterton), and the
suite's instruments do not see any of this: the reading council scored v3 4.0/4.0/4.0/4.0
while a human reader correctly diagnosed structural monotony and self-satisfaction.

That gap — the suite cannot see what the reader sees — is the next iteration's target.

## What the research changed

This iteration's diagnosis came from the validation audit of the prior change, not from
a fresh literature pass. The verdict reproduces the Goodhart shape the prior red-team
warned of, surfacing on a new axis: not decoration, but **monotony of figure**. The
liveness layer specifies a fixed set of moves and applies them at *high* intensity to
every paragraph; the writer becomes a metric-shaped author of metric-shaped prose.

Three signals diagnosed it concretely:

1. The reading council, which gave v3 4/4/4/4, has no axis for *template fatigue* or
   *self-satisfaction*. It scores each dimension within a paragraph or across the
   whole, never the *cross-paragraph repetition* that produces the metronome.
2. `lint_paragraph_motion` classifies paragraph shape but does not penalise running
   the same shape for paragraphs on end. It catches a flat-assertion section but not
   sixteen consecutive concession-turn structures.
3. The liveness layer's per-mode dial specifies which moves to make. It does not
   specify which moves *not* to repeat, and does not require any paragraph to refuse
   the running thesis.

The contemporary-pastiche charge is the second half of the same diagnosis. The corpus
calibration biases toward Carson/Dillard/Eiseley + Longfellow verse; that is a pre-1960
sensibility. Without a post-1950 prose model in the donor set, the writer reaches for
the diction the corpus prefers.

## Architecture

Extend the existing `VOICE` (russellian-voice) capability. No new capability slug — the
prior iteration's red-team established the principle and it still applies: extend
capabilities rather than proliferate them.

### Components

| File | New / Mod | Responsibility |
|---|---|---|
| `skills/russellian-style/scripts/lint_shape_variance.py` | new | Paragraph-shape-variance check. Reuses `classify_paragraph` from `lint_paragraph_motion` (stdlib). Flags any single shape that occupies ≥5 of any 6-consecutive-paragraph window, or ≥3 paragraphs in immediate succession. Returns `list[dict]`; one finding per offending run. Advisory severity. No spaCy, nothing from `lint_common`. |
| `skills/russellian-style/tests/test_shape_variance.py` | new | Test file named `test_shape_variance.py` (not `test_lint_*`) so the conftest's spaCy-absent `collect_ignore_glob` does not silently skip it in CI. Fixtures: a 6-paragraph monotone-shape document flags; a 6-paragraph varied document does not; a 3-in-a-row run flags. Deterministic. |
| `skills/russellian-style/scripts/lint_aphorism_density.py` | new | Aphorism-density signal, pure stdlib regex, quote-excluding via the same `_strip_quotes` pattern as `lint_ornament`. Flags closing sentences (last sentence of a paragraph) that match the fact-→-moral shape: 8–18 words, contains a humanity-generalising token (`we`, `our`, `us`, `ourselves`, `mankind`, `humanity`, `civilisation`, `modern life`, `most people`, `most of us`, `the rest of us`, `none of us`), and does not contain a concrete-instance marker (proper noun, year, numeric quantity). One finding per qualifying closer; `len(findings)` is the aphorism count, which `voice_eval` converts to per-1000-words density. Advisory severity. No spaCy, nothing from `lint_common`. |
| `skills/russellian-style/tests/test_aphorism_density.py` | new | Filename not `test_lint_*`. Positive fixtures: snails-v3-style chassis closers ("Most of our moral certainties have a snail at the bottom of them") flag. Negative fixtures: plainly-descriptive closers ("The crossing finished without an audience") do not flag; closers that name a proper noun or a date do not flag (the concrete-instance guard); quoted spans excluded. Deterministic. |
| `skills/russellian-style/scripts/voice_eval.py` | mod | Two-line addition to `_linters()`: register `shape_variance` and `aphorism_density`. No change to the liveness composite — the two new signals are advisory telemetry, reported alongside `ornament` in the linter densities table, not folded into the rolled-up number. |
| `skills/russellian-style/assets/system-prompts/{technical-exposition,narrative-editorial,polemic}.md` | mod | One directive appended to each mode's `## Liveness` subsection: the **self-turning paragraph mandate** (text below). Identical across the three modes — the mandate is structural and does not scale with the per-mode intensity dial. |
| `skills/russellian-style/references/longfellow-liveness-map.md` | mod | One bullet added to the "Disciplined-lyricism prose models" section: **Joan Didion** (post-1950, in copyright — referenced by named technique only, never quoted), describing the flat declarative as anti-aphorism and the refusal-of-the-moral move. |
| `skills/russellian-style/tests/test_system_prompt_liveness.py` | mod | One additional parametrized assertion: each mode's `## Liveness` subsection contains the self-turning mandate. Reuses the existing `MODE_DIAL` / `VALID_MODES` parametrize. |
| `openspec/changes/add-voice-anti-monotony/specs/russellian-voice/spec.md` | new | Spec delta: `ADD REQ-VOICE-018..025` (numbering continues from `add-longfellow-liveness` which used through 017; no renumbering). |
| `docs/audits/2026-05-28-snails-v3-vs-v3.1/` | new | Validation artifact, produced after the change lands: `snails-v3.1.md` (rewritten essay applying the design + Lippinus fix + Bernoulli mason irony), `scores.json` (telemetry for v3 vs v3.1 by the new instruments + reading council), and `README.md` (the comparison and honest caveats — same structure as the prior audit). |

## The two new signals (specifics)

### `lint_shape_variance.py`

Reuses `classify_paragraph(p) -> str` from `lint_paragraph_motion` (which returns one
of seven shape labels: `assertion_only`, `assertion_justification`, `concession_turn`,
`contrast`, `example_inference`, `question_answer`, `definition_by_pressure`). Both
the source and the import are stdlib.

The algorithm:

1. Split the document into paragraphs (`re.split(r"\n\s*\n", text)` + strip).
2. Classify each paragraph into one of the seven shapes.
3. Slide a 6-paragraph window. For each window, if any single shape occupies ≥5 of 6
   paragraphs (≥83%), emit one finding for that run.
4. Independently, scan for runs of ≥3 consecutive paragraphs with the same shape;
   emit one finding per run.

Each finding: `{"rule": "shape-variance", "shape": <label>, "start_paragraph": <0-indexed>, "run_length": <int>, "kind": "window"|"streak", "tier": "important"|"advisory", "severity": "advisory"}`. `tier` is `important` for streaks ≥4 or window dominations ≥6-of-6; otherwise `advisory`. Severity stays advisory regardless (the v1 convention for new vitality linters).

Calibration: the snails-v3 essay would produce two findings (the assertion_only run in
the middle, the concession_turn dominance at the close), the snails-v2 essay would
produce one, the snails-v1 essay would produce two (different shapes, same monotony).

### `lint_aphorism_density.py`

Pure stdlib regex. `lint_aphorism_density(path) -> list[dict]`.

The algorithm:

1. Read the document.
2. Apply `_strip_quotes` (the same per-line strip used in `lint_ornament`: double
   quotes, curly quotes, blockquote lines) so quotations and discussion of aphoristic
   sources are not penalised.
3. Split into paragraphs; for each paragraph extract the closing sentence (last
   non-empty sentence after splitting on `[.!?]+`).
4. Test the closing sentence against the aphorism shape:
   - word count is between 8 and 18 inclusive;
   - contains a humanity-generalising token (case-insensitive match against the
     closed list above);
   - does **not** contain a concrete-instance marker — defined as: a capitalised word
     that is not at sentence start (proxy for proper noun), a 4-digit year, or a
     numeric quantity (`\b\d+\b`). The concrete-instance guard is what distinguishes
     "Russell's table in this room earns the abstraction" (grounded — not aphorism)
     from "Most of us inherit our certainties from temperament" (ungrounded — aphorism).
5. Emit one finding per qualifying closer.

Each finding: `{"rule": "aphorism-density", "paragraph_index": <0-indexed>, "closer": <stripped sentence text>, "tier": "advisory", "severity": "advisory"}`.

`voice_eval`'s standard `len(fn(path)) / n_words * 1000` then yields aphorisms per
1000 words. A descriptive threshold (NOT a gate): **≥6 aphorisms per 1000 words is the
fault Charles named** ("performs wisdom on a metronome"). Documented in the linter's
module docstring as calibration, not encoded as a hard cutoff.

## The self-turning paragraph mandate

Appended to each mode's `## Liveness` subsection (identical text in all three; the
mandate is structural, not intensity-scaled):

> **Self-turning paragraph (mandate).** At least one paragraph per essay must
> complicate the running thesis, refuse it, or turn its irony on the essayist —
> *not* reinforce it. The reader notices the move you are running by paragraph four;
> if you have not broken it by paragraph eight, you are performing wisdom on a
> metronome. The break can take three shapes: a paragraph that lets the subject
> resist its own moral (the snail's slowness is a function of being eaten less than
> rabbits, not a critique of human haste); a paragraph that flattens to plain
> description with no verdict; or a Russell-shaped sentence that notices the
> essayist's habit and turns it on the essayist. Choose one, deploy it once. Do not
> let the break itself become a template.

The last line — "do not let the break itself become a template" — guards against the
recursion where the self-turning move becomes its own metronome.

## The Didion addition

One bullet appended to the "Disciplined-lyricism prose models" section of
`longfellow-liveness-map.md`, after the Eiseley entry:

> **Joan Didion** (post-1950, in copyright — referenced by named technique only,
> never quoted) — the flat declarative as anti-aphorism; the concrete list that
> argues without summarising; the refusal of the moral. The writer assembles exact
> details and lets the reader draw the conclusion the writer pointedly does not.
> *Slouching Towards Bethlehem*'s title essay is the canonical case: a catalogue of
> San Francisco scenes carries the argument, and the essayist refuses to state it.
> The technique counters the chassis fault diagnosed in the v3 snails essay — every
> paragraph performing a verdict — and widens the diction window beyond the
> Edwardian-familiar-essay register the existing donors share.

The five prose models then read as a deliberate spread: Carson (anaphoric
accumulation), Dillard (image-evolution), Eiseley (scale-collision), Didion
(refusal-of-the-moral), and the Longfellow verse anchors for cadence. The widened set
is the diction-widening half of the fix.

## Validation gate

The success artifact is **snails-v3.1**: a rewritten snails essay applying the new
self-turning mandate, with at least one paragraph from each of the three break
shapes (resist-its-own-moral, flatten-to-description, turn-on-essayist), and fixing
the two factual errors Charles caught (`Lippinus` not `Hirpinus`; the Bernoulli
stonemason carved an Archimedean spiral instead of the requested logarithmic one).

The audit bundle compares v3 vs v3.1 by:

- **The two new instruments.** v3 should flag `≥2` shape-variance findings and
  `≥6/1000` aphorism density; v3.1 should reduce both substantially (shape-variance
  to 0 or 1; aphorism density to ≤4/1000).
- **The reading council.** Same role-played five-persona protocol as the prior audit,
  blind ordering. Success condition: quality holds at ≥4, and at least one council
  dimension that the v3 critique identified (style or quality) shows movement.
- **The honest caveats.** Same disclosure as the prior audit: single-author non-blind
  rewrite; the suite scoring its own output; what the instruments do and do not
  measure.

## Rejected / deferred

- **Promoting either new linter to a hard gate.** Convention is advisory in v1 for all
  vitality linters. Same logic as `lint_ornament`. Deferred to a calibration follow-up.
- **Aphorism detection via LLM judge.** Higher precision but introduces a dispatcher
  dependency and slows the eval. Regex is YAGNI-correct for a v1 advisory signal.
- **Multiple post-1950 donors (Berger, Hass).** The user picked Didion alone. The
  others remain available for a future donor-expansion change if the diction-widening
  proves insufficient.
- **A new `voice-anti-monotony` capability slug.** Extend `VOICE`. The prior
  iteration's red-team established the principle and it still holds.
- **Folding the new signals into the liveness composite.** The composite is already
  saturating (cadence ceiling, concreteness absent). Adding more terms with their own
  ceilings would worsen the saturation. The new signals report alongside the composite,
  not inside it.

## Isolation and conventions

- Work in the git worktree at `~/.config/superpowers/worktrees/russellian-book-suite/feat-voice-anti-monotony`,
  on `feat/voice-anti-monotony` based on `feat/longfellow-liveness`.
- The parallel agent's checkout (`russell-pass-agentic-civ` in the main repo) stays untouched.
- PR base at finish time: `feat/longfellow-liveness` (stacked PR) until that branch merges to main, then rebase onto main.
- OpenSpec change `add-voice-anti-monotony`; spec deltas continue REQ numbering at `REQ-VOICE-018` (no renumbering).
- Terse commits, no AI attribution. TDD per task. New code stays import-safe under the CI `[ci]` extra (no top-level spaCy).

## Sources

- In-repo: `references/russellian-vitality-guide.md`; `references/longfellow-liveness-map.md`;
  `scripts/lint_paragraph_motion.py`, `lint_ornament.py`, `voice_eval.py`;
  `docs/audits/2026-05-27-snails-before-after/` (v1, v2);
  the v3 snails essay produced for this critique.
- The critique itself (the diagnostic that named the chassis fault, the
  self-satisfaction problem, and the pastiche register).
- Joan Didion, *Slouching Towards Bethlehem* (1968), title essay — referenced by
  technique, not quoted.
