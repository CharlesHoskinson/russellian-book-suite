# Spec delta — voice-eval

Capability: `VOICE-EVAL` (voice-eval). REQ prefix `VEVAL` to match the existing
`add-voice-eval-stage` change (REQ-VEVAL-001..008); this change ADDs REQ-VEVAL-009..017
for the 20×20 comparison harness, the formula-drift monitor, and the blind A/B
human-study scaffold.

## ADD REQ-VEVAL-009 — Ubiquitous

The voice-eval skill shall provide a 20×20 comparison harness that takes 20 prompts
stratified across the three registers and generates one passage per prompt from each
of `triadic-voice` (v1) and `triadic-voice-v2` (v2), producing 40 passages.

## ADD REQ-VEVAL-010 — Event-driven (equal-grounding gate)

When the harness runs, every one of the 40 passages shall be required to clear the
russellian-style v1 floor; any passage that fails shall be regenerated before scoring,
so both arms are equally floor-clean.

## ADD REQ-VEVAL-011 — Ubiquitous (metric deltas)

The harness shall score all 40 passages on the eight liveliness signals and report,
per signal, the mean delta between the v2 and v1 arms, overall and per register.

## ADD REQ-VEVAL-012 — Ubiquitous (blind pairwise judge)

The harness shall run a blind pairwise judgment of each prompt's v1/v2 pair in-session,
with the presentation order swapped (each pair judged in both orders), length-matched,
and a chain-of-thought rationale required; it shall collect a forced-choice keep
decision, a "which made you want the next sentence more" decision, and ordinal ratings
for momentum, clarity, voice-authority, readability, and trustworthiness; and it shall
report a win-rate with confidence intervals.

## ADD REQ-VEVAL-013 — Ubiquitous (formula-drift monitor)

The harness shall compute a formula-drift report within each arm's 20 passages using
TF-IDF cosine similarity over structure-only tokens of first and last sentences, plus
opening part-of-speech patterns and analogy-family reuse, and shall flag drift above a
configured threshold.

## ADD REQ-VEVAL-014 — Unwanted behaviour (no detector gate)

If an AI-text-detector or perplexity score is computed, then it shall be reported as
advisory only and shall never gate, fail, or block any passage.

## ADD REQ-VEVAL-015 — Ubiquitous (success criterion)

The harness shall report the 20×20 as passing only when the v2 arm stays floor-clean,
scores higher than v1 on the positive signals, wins more than half the pairwise
judgments, does not score worse on trustworthiness, and shows lower formula drift.

## ADD REQ-VEVAL-016 — Ubiquitous (human-study scaffold)

The skill shall provide a blind A/B human-study scaffold (prompt set of at least 50–60
items, randomized presentation, a rater rubric covering the targeted dimensions, and
inter-rater reliability via Fleiss' kappa or Krippendorff's alpha).

## ADD REQ-VEVAL-017 — Event-driven (signal graduation)

When a positive signal is proposed for promotion from advisory to gating, the human
study shall be required to show a moderate positive Spearman correlation with the
targeted human dimension whose bootstrap confidence interval excludes zero, and
promotion shall be denied if it degrades the trustworthiness rating.
