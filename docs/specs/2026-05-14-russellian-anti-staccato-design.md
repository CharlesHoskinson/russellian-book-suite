# russellian-style anti-staccato — Design

Date: 2026-05-14
Author: Charles
Status: Draft, pending user approval

## Problem

The `russellian-style` skill ships eleven linters: six negative
(hedges, passive voice, signal density, parallel structure, sentence
rhythm, listicle abstraction) and five vitality-tier advisory
(burstiness, ai-vocabulary, concrete-instance density, epistemic
precision, paragraph motion). The negative linters catch many ways
prose can fail; the vitality linters reward concrete instances,
varied sentence lengths, exact uncertainty, and paragraph shape.

The composite still passes prose that is rhythmically dead. The
research note at `docs/research/2026-05-14-russell-style-enhancement.md`
demonstrates this against a 20-paragraph claim-ledger sample: the
output is lint-clean but reads as a wall of compact assertion + compact
justification pairs. A recent Bitcoin generation reproduced the
failure mode. The bad prose comes in three patterns the existing
linters do not flag:

- **Negation-affirmation template.** "X is not Y. X is Z." repeated
  across paragraphs. Each paragraph passes sentence-rhythm and
  parallel-structure; the repetition between paragraphs is invisible.
- **"This is …" conclusion stacking.** Three or more paragraphs end
  on a sentence starting with `This is` or `It is`, each declaring
  the prior assertion's identity.
- **Abstract-subject runs.** Four or more consecutive sentences share
  the same abstract noun subject (`system`, `protocol`, `ledger`,
  `truth`, `freedom`). Burstiness and paragraph-motion treat each
  paragraph as a sample; they do not catch subject monotony inside a
  paragraph.

The `lint_paragraph_motion` flat-proportion metric does fire on this
prose (the existing runbook and concepts doc both register
flat_proportion ≥ 0.93). The signal is right but advisory and the
skill provides no concrete redirection.

The user's instructions provide the canonical failure example and a
matched Russellian rewrite (see Appendix). The skill should detect
the patterns, point at the offending paragraphs, and show the operator
where Russell's analytic-with-motion cadence diverges from staccato.

## What ships

One new linter, a positive-checks aggregation in the style-pass
report, three documentation updates, two regression fixtures, and an
appendix to the existing research note. All findings remain advisory.
No existing linter signature, severity, or test fixture changes.

### 1. New linter `scripts/lint_ai_staccato.py`

Four rules, each emitting JSON findings with the standard
`{rule, tier, severity, line, …}` shape:

- `staccato-paragraph-run` — fires when 3+ consecutive paragraphs each
  contain 2-3 sentences AND every sentence is ≤ 12 words. Targets the
  cross-paragraph pattern that existing linters miss; single-paragraph
  staccato is already covered by `lint_sentence_rhythm` and
  `lint_burstiness`. Reports the start line of the run plus the run
  length.
- `negation-affirmation-template` — fires when 2+ paragraphs match
  the regex shape `<NP> is not <X>\. <NP> is <Y>\.` (any noun
  phrase, anchored on the period). The two paragraphs may share the
  same NP or different NPs; the template is what matters.
- `this-is-conclusion-overuse` — fires when 3+ paragraphs in a
  window have their final sentence start with `This is `, `It is `,
  or `These are `.
- `abstract-subject-run` — fires when 4+ consecutive sentences (within
  one paragraph or across paragraph boundaries) carry the same
  abstract noun as grammatical subject. The abstract noun list is
  parameterised in `assets/russellian-rules.json`.

Severity: `advisory`. Tier: `important`. Same JSON shape and CLI as
the existing vitality linters; same `lint_common.load_markdown` helper
and per-paragraph segmentation.

### 2. `scripts/style_pass_report.py` updates

- Add `lint_ai_staccato` to the linter inventory.
- Add a **positive-checks block** to the report dict:

  ```json
  {
    "positive_checks": {
      "sentence_length_fano": <float>,
      "paragraph_shape_diversity": <float>,
      "concession_turn_count": <int>,
      "concrete_instance_count": <int>,
      "template_repetition_rate": <float>
    }
  }
  ```

  `sentence_length_fano` reuses the burstiness lint's Fano-factor
  computation. `paragraph_shape_diversity` reuses the paragraph-motion
  classification (assertion / question / contrast / example /
  consequence) and reports the Shannon entropy of the distribution.
  `concession_turn_count` is a regex pass for paragraph-internal
  `But …`, `However …`, `Yet …`, `Still …`, `It is true that … but
  …`. `concrete_instance_count` reuses the
  concrete-instance-density lint's NER + occupational-noun counts.
  `template_repetition_rate` is the new lint's negation-affirmation
  hit count divided by paragraph count.

- Output is informational. The report does not gate on any positive
  check.

### 3. `references/russellian-style-guide.md` revision

- Reframe `no hedging` → `no vague hedging; bounded uncertainty
  permitted`. Carry over the existing examples; add one example of
  legitimate bounded uncertainty (taken from Russell's *Problems of
  Philosophy* preface paraphrase, already in the corpus map).
- New section `Anti-staccato`. Show the user-provided Bitcoin pair
  verbatim with byline `bad — passes all six negative linters but
  fails staccato-paragraph-run + this-is-conclusion-overuse` and
  `good — passes both negative and staccato`.
- New section `Concession-turn structure`. The four-move template:
  (1) state the common view, (2) grant its partial force, (3) draw
  the distinction, (4) state the consequence. Two examples.

### 4. `references/before-after-examples.md` additions

Three new contrast pairs, each labeled with the specific motion that
changed:

- Bitcoin staccato → Russellian (the canonical pair from the user
  prompt).
- Abstract-noun-subject overuse → particular-subject variation.
- "This is …" stacking → consequence-carrying turn.

### 5. `assets/russellian-rules.json` updates

Add an `ai_staccato` rule entry:

```json
{
  "id": "ai_staccato",
  "tier": "important",
  "severity": "advisory",
  "detection": {
    "staccato_run_min": 3,
    "staccato_max_sentence_words": 12,
    "staccato_max_sentences_per_paragraph": 3,
    "negation_affirmation_min_paragraphs": 2,
    "this_is_window": 6,
    "this_is_min": 3,
    "abstract_subject_min_run": 4,
    "abstract_subject_stoplist": [
      "system", "protocol", "ledger", "truth", "freedom",
      "pipeline", "result", "process", "thing", "framework",
      "approach", "principle"
    ]
  }
}
```

The stoplist is short by design. The lint targets generic abstract
nouns that signal subject monotony; domain-specific subjects (Bermuda,
Russell, Bitcoin) stay invisible to the rule.

### 6. Tests

- `tests/test_lint_ai_staccato.py`. Per-rule positive and negative
  case. Each fixture under `tests/fixtures/ai_staccato/` is a small
  markdown file: `staccato_run.md`, `staccato_run_clean.md`,
  `negation_affirmation.md`, `this_is_stacking.md`,
  `abstract_subject_run.md`, plus matched clean counterparts.
- Extend `tests/test_style_pass_report_vitality.py`. Assert the
  `positive_checks` block is present with all five fields and the
  staccato lint contributes its findings to the report dict.
- Add `tests/test_lint_ai_staccato.py::test_anthropic_compliance`
  case (or extend `test_anthropic_compliance.py`) to assert the new
  rule entry exists in `russellian-rules.json`.
- Existing tests stay unchanged unless they encode terse behaviour.

### 7. Bitcoin comparison samples

Two fixture files at `tests/fixtures/before_after/`:

- `bitcoin_staccato.md` — 10 paragraphs reproducing the failure
  mode. Hits `staccato-paragraph-run`,
  `negation-affirmation-template`, and `this-is-conclusion-overuse`.
- `bitcoin_russellian.md` — 10 paragraphs of analytic-with-motion
  prose. Passes the new lint and the existing eleven.

Both are used as regression fixtures: a test loads each file, runs the
new lint plus the six negative linters, and asserts the staccato
sample fires the expected rules while the Russellian sample stays
silent.

### 8. Research-doc appendix

Append a dated section to
`docs/research/2026-05-14-russell-style-enhancement.md`:

- Heading `Anti-staccato fix (2026-05-14)`.
- The bad and good 10-paragraph Bitcoin samples (linked, not inlined).
- A two-paragraph analysis listing the specific motions that changed
  paragraph-by-paragraph.
- The lint-output diff (counts of fires before vs after).

## Out of scope

- Changes to existing linter signatures, severities, or rule
  parameters.
- Mode-keyed system prompt revisions (already shipped and adequate).
- LLM-driven generation of the new Bitcoin sample. The sample is
  hand-authored to demonstrate the target style and to serve as a
  regression fixture.
- Promoting any vitality check to gating critical (research-doc
  guidance: do not gate before broader calibration).
- Changes to `book-compose` integration. The skill's existing prose-
  mode hand-off via `style_pass_report.generate_report_dict` already
  carries the report dict and will pick up the new fields for free.

## Constraints honored

- No marketing voice.
- No ornament for ornament's sake.
- No weakening of clarity, hedge, passive, or signal-density checks.
- All scope contained to `skills/russellian-style/`, its tests, and
  one appendix in `docs/research/`.

## Architecture and data flow

```
markdown input
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  Six negative linters (unchanged)                       │
│  + Five vitality linters (unchanged)                    │
│  + lint_ai_staccato.py (NEW)                            │
└─────────────────────────────┬───────────────────────────┘
                              │ JSON findings
                              ▼
                  ┌─────────────────────────────┐
                  │  style_pass_report          │
                  │                              │
                  │  - linter findings           │
                  │  - positive_checks (NEW)    │
                  │  - mode-keyed summary       │
                  └──────────────┬──────────────┘
                                 │ report dict
                                 ▼
                       book-compose prose_mode
                       (consumes report dict;
                        no integration change)
```

The new linter is a sibling of the existing five vitality linters; it
imports `lint_common` for markdown loading and paragraph segmentation
and follows the same per-paragraph traversal. The positive-checks
block is computed at the report level by aggregating data already
produced by other linters plus a small concession-turn regex pass.

## Estimated effort

- New linter + four rules + tests: 0.5 day.
- Style guide + before/after edits + rules.json: 0.25 day.
- Bitcoin samples (bad + good): 0.5 day. The good sample is the
  expensive part; it must read as Russell.
- style_pass_report extension + tests: 0.25 day.
- Research appendix + lint-diff: 0.25 day.

Total: ~1.75 days.

## Open questions

1. Stop-list scope. The abstract-noun stoplist currently lists 12
   generic words. Extending to domain-specific abstractions (e.g.
   `verifier`, `pipeline`, `workspace`) would let the lint fire on
   the runbooks too, which may or may not be desirable. Decision: keep
   the list generic for v1; revisit after the new Bitcoin sample
   ships.

2. Concession-turn detection precision. Regex on `But / However / Yet /
   Still` over-counts when those words appear mid-sentence in non-
   concessive contexts. A dependency-parse approach would be more
   precise but adds spaCy dependency and runtime cost. Decision: stay
   with regex for v1; mark in the rules.json doc that the count is a
   lower bound for ergonomics, not a precise metric.

3. Sample regeneration cadence. Should the Bitcoin good-sample be
   regenerated periodically as the skill evolves? Decision: no — it
   is a regression fixture, not a moving target. If the skill
   improves, write a new fixture; do not edit the old.

## Appendix — user-provided canonical pair

The pair below comes from the user prompt and serves as the
documentation example, the test fixture seed, and the calibration
target.

**Bad (staccato):**

> Speculation has obscured the philosophy. Many men bought Bitcoin not
> because they desired sound money, but because they desired more
> dollars. This is not a contradiction in the protocol. It is a
> contradiction in the buyer.

**Good (Russellian):**

> Those who call Bitcoin a mere speculation have seized upon a real
> defect and mistaken it for the whole subject. It is true that many
> men bought it in the hope of selling it to a more excited neighbour.
> But this tells us more about men than about the protocol. A system
> may be philosophically interesting even when most of its admirers
> understand it badly.

As written above, the bad version is a single paragraph with four
short sentences. On its own it fires `negation-affirmation-template`
(`This is not …. It is …`) and contributes one tick toward
`this-is-conclusion-overuse`. The full 10-paragraph fixture extends
this shape across the sample so that `staccato-paragraph-run` and
`this-is-conclusion-overuse` both fire. The good version preserves
sentence-length variance, paragraph dependency, and shape diversity
so that the same checks stay silent across its full 10 paragraphs.
