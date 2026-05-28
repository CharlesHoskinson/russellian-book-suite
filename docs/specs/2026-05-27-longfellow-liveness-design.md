# Longfellow × Russell liveness blend — design

Date: 2026-05-27
Status: approved direction; awaiting plan
Change: `openspec/changes/add-longfellow-liveness/`

## Problem

The russellian-style voice is compliant but, an external reader judged, "more
decorative than Russell" — strong in spirit, weaker in execution, because too many
paragraphs ran the same jeweled circuit. The goal is to make the writer **livelier**:
more rhythmic drive, more forward momentum, more argument-anchored concrete image —
without amplifying the decoration that was the diagnosed fault.

The organizing idea is to blend Henry Wadsworth Longfellow's poetic strengths into the
analytic prose. The trap is obvious and was flagged in review: Longfellow is a
sentimental Romantic poet, and importing him naively pushes *toward* the disease. So the
blend imports his **rhythm/cadence, forward momentum, and concrete sensory imagery** and
firewalls his **sentiment, archaism, apostrophe, and ornament**.

## What the research changed

A research-and-red-team pass (literature search plus two adversarial reviews) corrected
the first-draft design on four points. The corrections are load-bearing:

1. **Do not build a parallel scorer.** The repo already ships a vitality program —
   `references/russellian-vitality-guide.md` (six positive rules), `lint_burstiness.py`
   (Fano factor), `lint_concrete_instance_density.py`, and `lint_paragraph_motion.py`
   (a paragraph-shape/momentum detector). A new composite "liveness score" would be a
   third burstiness implementation. We **compose the existing instruments** instead.

2. **A naive liveness metric rewards the failure mode.** A score that rewards
   sensory-noun density and sentence-length swings rewards exactly the jeweled prose the
   reviewer disliked; the snails rewrite *improved* by becoming less decorative. The fix:
   reward **argument-anchored concreteness** (concrete instances/examples, which
   `lint_concrete_instance_density` already measures) and add an **ornament penalty** that
   *punishes* decoration. Reward the instance; penalize the jewel.

3. **Cadence must be order-sensitive.** The Fano factor (variance/mean of the multiset of
   sentence lengths) is permutation-invariant — it cannot tell an artful long→short
   rhythm from a random shuffle, because rhythm *is* the ordering. We use the
   **nPVI** (normalized pairwise variability index; Grabe & Low 2002), an adjacent-pair
   contrast measure, with a minimum sentence-length floor to resist fragment-stuffing.

4. **"Radically improve liveness" needs a judge.** A deterministic score cannot certify
   liveness; only a reader can. We make the **reading council** the judge: a blind
   before/after A/B (it captured the snails verdict faithfully). The deterministic
   signals are descriptive telemetry only — no "beats the Russell baseline" claim, and the
   word "radically" is dropped until human-correlation evidence exists.

The donor framing follows the same logic: keep **Longfellow** as the headline donor for
rhythm and image, but ground the technique anchors in the tradition of **disciplined
lyricism** — Carson, Dillard, Eiseley — whose rule is that *every image does
argumentative work; it is a vehicle, not cargo*. That is also Russell's own method
(the hungry cat in the cage).

## Architecture

The change extends two existing capabilities (no new capability):

- **`VOICE` (russellian-voice)** — the prompt liveness layer and a new ornament guard.
- **`VOICE-EVAL` (voice-eval)** — the nPVI signal, the composed liveness summary, and
  before/after reporting.

### Components

| File | New/Mod | Responsibility |
|---|---|---|
| `tools/build-longfellow-corpus/` | new | Dev-time, run-once. Pulls public-domain Longfellow from Gutenberg **via scrapling-fetch's CLI as a subprocess** (the suite's network boundary), poetry-aware segmentation, emits the study-corpus index. Lives in `tools/` because corpus building is owned there (`tools/build-russell-corpus/` precedent), not in the skill. |
| `skills/russellian-style/assets/longfellow-corpus/index.json` | new | Study-corpus index: source pointers (title/url) + **short verified quote snippets** + structural locators (canto/stanza) + technique tags. Snippets, not `line_hint`-into-HTML (no code resolves `line_hint`, and Gutenberg HTML line offsets are unstable). Longfellow is public domain, so verbatim snippets are permitted. |
| `skills/russellian-style/references/longfellow-liveness-map.md` | new | The derived **prose-translatable** techniques, each with a verified anchor and the firewall, framed "borrow cadence and image-logic, never meter, rhyme, archaism, or sentiment." |
| `skills/russellian-style/assets/system-prompts/{technical-exposition,narrative-editorial,polemic}.md` | mod | Add a `## Liveness` subsection to each `# Calibration and planning` block, at the per-mode dial. |
| `skills/russellian-style/scripts/lint_ornament.py` | new | Pure-regex decoration guard (advisory). Flags purple-prose markers; excludes quoted spans. No spaCy import (CI-safe). |
| `skills/russellian-style/scripts/voice_eval.py` | mod | Add the nPVI cadence signal (stdlib) and a composed liveness summary; report before/after; make no "beats baseline" claim. |
| tests | new | Ornament linter, nPVI signal, liveness composite, and per-mode liveness-contract assertions. All CI-safe; spaCy-gated where they touch spaCy-backed linters. |
| `docs/audits/2026-05-27-longfellow-liveness-before-after/` | new | The validation bundle: blind reading-council A/B on a baseline vs. blended passage. |

## The liveness layer (the real change)

Each mode prompt gains a `## Liveness` subsection under `# Calibration and planning`,
expressed as **gradable** directives (what each level permits and excludes), at the
per-mode dial: **technical-exposition = low, narrative-editorial = high, polemic =
medium**. The directives are drive-oriented, drawn from the craft literature:

- **Sentence-length percussion** (Le Guin): after a cluster of similar-length sentences,
  a markedly shorter one to mark *arrival*. Low = vary every ~5 sentences; high = every 2.
- **Cumulative / base-clause-first construction** (Christensen): state the claim, then add
  free modifiers each zooming to something more specific. Forward motion, not suspension.
- **Knot-and-resolution cadence** (Stevenson): set up a tension early in the sentence,
  resolve it on the *narrower* term at the end — Russell's own architecture.
- **Anaphora tied to the argued term** (not atmospheric repetition).
- **One concrete anchor per abstraction** (Strunk/White Rule 16): the smallest specific
  physical thing that instantiates the claim; chosen for precision, not beauty.

Each subsection carries at least one **liveness anchor**: a flat sentence paired with a
livelier rendering, with the firewall stated. Verbatim quotation is restricted to
**public-domain Longfellow** (attributed to a corpus snippet); the in-copyright prose
models (Carson, Dillard, Eiseley) are referenced **by named technique only, never
quoted**.

## The ornament guard (`lint_ornament.py`)

Pure-stdlib regex, advisory severity (matching the other vitality linters in v1), with a
quote-exclusion pass. Flags the markers that distinguish purple from lively:

- adjective stacking (≥2 evaluative modifiers on one noun)
- adverb amplifying an already-strong verb ("roared loudly")
- abstract emotion words applied directly without a concrete vehicle
- apostrophe ("O Reader!")
- archaic diction tokens (`o'er`, `'tis`, `thee`, `thou`, `doth`, `ere`, `'neath`)
- nature-mirrors-mood clauses

It imports nothing from `lint_common` (which imports spaCy at module top and breaks under
the CI `[ci]` extra). Limits are honest: regex cannot see metrical sing-song, rhyme, or
tonal sentiment achieved with modern vocabulary; the design documents these as unguarded
and leaves them to the reading-council A/B.

## The measurement (compose, don't re-implement)

`voice_eval` gains:

- **nPVI cadence signal** — `nPVI = (100/(N-1)) · Σ |L_k − L_{k+1}| / ((L_k + L_{k+1})/2)`
  over sentence lengths `L`, computed with `statistics`/`str.split` only (the stdlib
  pattern already in `reading_scores.py`), excluding sentences below a word floor.
- **liveness summary** — assembled from instruments that already exist: paragraph-motion
  variety (`lint_paragraph_motion`), concrete-instance density
  (`lint_concrete_instance_density`), and the nPVI signal, **minus an ornament penalty**
  from `lint_ornament`. No re-implementation of burstiness or concrete density.
- **before/after** — when a baseline text is supplied, report generated vs. baseline side
  by side, as telemetry. **No "beats baseline" verdict.**

## Validation gate

Success is **not** a higher number. Success is a blind reading-council A/B (baseline vs.
blended passage) in which the council's **flow and enjoyment rise without quality
falling** — the same instrument and trade-off shape that captured the snails verdict. The
audit bundle records both the council scores and the deterministic telemetry, and is the
artifact that justifies the change.

## Rejected / deferred

- **A new `voice-liveness` capability and standalone `liveness_score.py`** — rejected;
  duplicates the existing vitality program.
- **Fano factor for cadence** — rejected; order-blind. Replaced by nPVI.
- **A sensory-concreteness lexicon** (Brysbaert 2014; Lancaster Sensorimotor Norms,
  CC-BY 4.0) for imagery — deferred; it is a new instrument, and argument-anchored
  concrete-instance density already supplies the right (non-decorative) imagery signal.
  Noted as a future enhancement if the A/B shows imagery is the limiting factor.
- **Promoting the ornament guard to a hard gate** — deferred; all vitality linters are
  advisory in v1 by repo convention, pending calibration against persona findings.
- **`line_hint`-into-HTML corpus pointers** — rejected for verse (unstable, unresolved by
  any code). Verified snippets + structural locators instead.

## Isolation and conventions

- Work is isolated in a git worktree off `origin/main` on `feat/longfellow-liveness`; the
  parallel agent's checkout is untouched.
- OpenSpec change `add-longfellow-liveness`; spec deltas continue REQ numbering at
  `REQ-VOICE-008` and `REQ-VEVAL-009` (no renumbering).
- Ships as branch + PR, squash-merged. No AI attribution in commits, files, or comments.
- TDD per task; no live LLM calls in tests; new code stays import-safe under the CI
  `[ci]` extra (no top-level spaCy).

## Sources

- In-repo: `references/russellian-vitality-guide.md`; `scripts/lint_paragraph_motion.py`,
  `lint_burstiness.py`, `lint_concrete_instance_density.py`;
  `skills/review-conductor/scripts/reading_scores.py`; `tools/build-russell-corpus/`.
- nPVI: Grabe & Low (2002), normalized Pairwise Variability Index.
- Fano permutation-invariance: it is a statistic of the multiset of sentence lengths.
- Metric-gaming caution: Powers et al. (ETS, 2001), "Stumping E-Rater."
- Prose-rhythm craft: Le Guin, *Steering the Craft*; Christensen, *Generative Rhetoric of
  the Sentence*; Stevenson, "On Some Technical Elements of Style"; Strunk & White, Rule 16.
- Disciplined lyricism: Rachel Carson, Annie Dillard, Loren Eiseley; Connolly's
  Mandarin/vernacular synthesis (*Enemies of Promise*).
- Deferred lexicons: Brysbaert, Warriner & Kuperman (2014) concreteness norms; Lynott &
  Connell et al. (2019) Lancaster Sensorimotor Norms (CC-BY 4.0).
