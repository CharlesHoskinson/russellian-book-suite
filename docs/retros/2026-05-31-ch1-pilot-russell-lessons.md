# Russellian-style: lessons from the Chapter 1 pilot

Aggregated from writing and gating "Intelligence Is Not Civilization" end-to-end.
What changed in the skill is listed at the end.

## 1. The vitality half is the value; the negative linters only punish

The deterministic linters (hedges, passive, signal-density, listicle, rhythm) can
punish bloat but cannot reward a concession, a concrete instance, or a paragraph that
earns its last sentence. The first ch1 draft passed the negative linters and still
read as machine prose. The fix came from the vitality guide and the corpus anchors,
not the linters. Lead with the positive moves; treat the negative linters as a floor.

## 2. The negation-affirmation wall is the canonical machine tell

"X is not Y. X is Z." / "This is not A. It is B." stacked across paragraphs passes
every negative linter and still reads as a wall. `lint_ai_staccato` is the highest-
signal linter and must be run; it was *missing from the stale runtime copy*, which is
why the first cleanup missed the staccato. Fix with a move (concession / distinction /
turn), not a punctuation swap.

## 3. The delta needs a diagnostic, not just a number

`score_russell_delta` emitted only the Delta; during calibration the per-word z-scores
had to be computed by hand. Added `--diagnose`. The recurring pattern: machine analytic
prose **over-uses emphatic absolutes** (never, cannot, no, nothing, real) and bare
"it"/"and", and **under-uses subordinators** (of, which, but, if). Calibrating toward
Russell is the same as the vitality work, and it improves the prose.

## 4. Do not hunt single words; the Delta can backfire

Trimming one *under-used* word ("a handful **of** tools" → "a few tools") raised the
Delta. Edit for the move, re-score. And the Delta is advisory: prose at p90 is as
Russellian as Russell's own 90th-percentile paragraph. Chasing the last thousandth is
the lexical hacking the guide exists to prevent.

## 5. The linters are candidate-detectors; contracts must use realistic thresholds

A chapter contract gating every linter at `== 0` fails on genuine analytic prose:
- `hedge_count` flags deontic "may" ("the model **may** reason") and counterfactual
  "could" — legitimate; the policy bans *vague* hedging, not exact uncertainty.
- `passive_voice_ratio` is a correct true-passive detector; good analytic prose runs
  ~0.10–0.13 ("are performed", "is owed"). `< 0.10` is stricter than Russell.
- `modifier_budget_violations` flags precise paired adjectives ("private and lossy").
Keep anti-slop / correctness gates strict (ai_fingerprint, listicle, rhythm, citation).

## 6. Deontic/epistemic modality does not separate by a clean rule

An attempt to make `lint_hedges` skip deontic "may"/counterfactual "could" via a
stative-head spaCy rule broke three tests that intend "may + action" as possibility
hedges. Deontic "may reason" and epistemic "may drop" are identical on the surface.
This is a policy/threshold matter, not a linter fix.

## Changes made to the skill (all under test)

- **`lint_hedges`** — skip contrastive/preference "rather … than" (BUG-4). Test added.
- **`score_russell_delta`** — new `diagnose()` / `--diagnose` calibration-lever mode.
  Three tests added.
- **`SKILL.md`** — surface `lint_ai_staccato`, the delta scorer + `--diagnose`, and an
  acceptance-threshold guidance section for contract authors.
- **`references/russellian-vitality-guide.md`** — "Calibrating to the delta band" and
  "The negation-affirmation wall" sections.
- Contract template thresholds (in `book-compose`) aligned to the no-vague-hedging
  policy: `hedge_count <= 6`, `passive_voice_ratio < 0.15`, `modifier_budget <= 10`.

Cross-reference: `docs/audits/2026-05-31-pilot-bug-ledger.md` (BUG-0..7, stage gates).
