# HFR v2 — Liveliness Signals, Floor Calibration, Chassis Variation, and the 20×20 Test

**Status:** Approved design (2026-06-19). Source: two deep-research reports on
making the HFR (Hoskinson–Feynman–Russell) generator more lifelike, plus eight
primary papers fetched and read (`hfr-deep-research/papers/`). OpenSpec change:
`openspec/changes/add-hfr-v2-liveliness/`.

## Goal

The current suite enforces a **negative discipline floor** — it removes AI tells
(hedging, passive voice, modifier bloat, AI staccato, uniform rhythm). Defect-free
is not the same as alive. Two failure modes are documented on the sample artifact
(`examples/triadic-trust-decomposition.md`): (1) **pass-but-flat** — text clears
every floor linter and still reads mechanical; (2) **false positives against real
energy** — a deliberate anaphoric drumbeat was flagged and softened, and the
keyword analogy/curiosity rewards failed to see obvious analogy and curiosity.

v2 adds **positive, advisory signals for enacted explanation**, **calibrates the
floor by register**, **fixes the two false positives**, **diversifies the chassis**,
and ships a **20×20 comparison** as the acceptance test — without weakening the
accuracy floor. The thesis from the research: *the next gains come not from
relaxing Russell, but from rewarding drumbeat, mapping, setup-payoff, and
action-bearing diction, and from moving fixed global budgets to corpus-conditioned,
register-conditioned corridors.*

## Decisions locked (user-approved 2026-06-19)

1. **Scope:** the full eight-item roadmap (four linter changes, two
   generation-guidance items, two evaluation items).
2. **Coexistence:** parallel skills with **v1 frozen as the control**; the floor's
   behaviour is versioned by *ruleset*, not by forking the skill.
3. **20×20 judging:** floor-clean gate + positive-signal metric deltas + a blind
   pairwise LLM-as-judge run (order-swapped, CoT), in-session.
4. **Grounding:** the design rests on the primary papers, with four corrections
   (below) applied over the reports' summaries.

## Source-paper corrections applied

Reading the primary sources moved four choices away from the reports:

1. **Verb-energy targets light-verb *constructions*, not nominalization suffixes**
   (cmp-lg/9503010: support-verb constructions; support-verb choice is
   corpus-specific). Protects domain nouns ("arithmetization", "verification").
2. **Burstiness uses a two-sided percentile *corridor*, not a lone Coefficient of
   Variation** (1805.01460: sentence length is robust, and rhythm carries
   long-range autocorrelation a single CV is blind to and that short-punchline
   padding games). CV is one component; DFA/autocorrelation is a noted future
   enhancement.
3. **AI-text detectors never gate** (2412.05139: TPR as low as 0% at 1% FPR, easy
   evasion). Any perplexity/detector read is advisory-only and skeptical.
4. **Authorial-distance is a distributional proxy, not a fine-tuned LM**
   (2401.12005: ALMs need fine-tuned causal LMs and 40–400 tokens; 57 paragraphs
   is too little). Use POS-n-gram / cadence-vector divergence from the profile.

Confirmed as-is: concreteness norms are real and LLM-alignable (2506.22439);
sentence length is a robust structural signal (1805.01460); task framing shifts
style measurably, justifying register dials + chassis rotation (1702.01841);
adaptive imitation beats copying, supporting a per-beat retrieval loop (RePA,
2505.18859); the G-Eval self-preference bias cancels in a v1-vs-v2 comparison
because both arms are LLM-generated (2303.16634).

## Architecture (Approach A — separated v2 skills)

| Unit | Type | Purpose |
|---|---|---|
| `hoskinson-style-profile.json` | shared artifact | corpus-derived cadence/diction/device statistics, per register |
| `liveliness-signals` | **new skill** | the 8 positive paragraph scorers + the corpus profiler; advisory |
| `russellian-style` | versioned ruleset | floor; v1 ruleset frozen, v2 ruleset adds drumbeat exemption + register corridors |
| `feynman-style` | edited | keyword analogy/curiosity rewards delegate to `liveliness-signals` |
| `triadic-voice` / `triadic-voice-v2` | frozen / **new skill** | v1 control generator / v2 chassis+register+profile generator |
| `voice-eval` | **new skill** | 20×20 harness, formula-drift monitor, human-study scaffold |

**Invariant preserved:** the negative floor stays hard and separate; the positive
signals are advisory and separate. The floor never imports the signals; the
generator consults both. Each unit is independently testable and composes via
`sibling_skills`.

## Component 1 — Corpus style-profile

`liveliness-signals/scripts/build_corpus_profile.py` runs offline over the 57
curated paragraphs + cleaned transcripts and emits
`assets/hoskinson-style-profile.json`, **per register** (technical-exposition /
narrative-editorial / polemic):

- sentence-length percentile corridors (`p10…p90`) and CV
- first-word distribution, discourse-marker frequency, direct-address rate
- short-pivot-to-long-unpacking ratio, mean inter-example spacing
- concreteness baseline (mean Brysbaert noun score), light-verb-construction rate
- a domain/glossary noun allow-list

Statistics only — never verbatim text (copyright-safe). Consumed by both the
linters (thresholds) and `triadic-voice-v2` (targets). Deterministic for fixed
input.

## Component 2 — Floor calibration (`russellian-style` v2 ruleset)

Shipped as `assets/russellian-rules-v2.json`; linters gain `--ruleset`/`--register`.
The v1 ruleset is byte-frozen, so the control is unchanged.

### Rhythm drumbeat exemption

A repeated-opening run is **exempt and credited `parallel-list`** when *all* hold:
1. the repeated opener is syntactically shallow (DET/PRON/function word);
2. the following head nouns/predicates are semantically distinct and progressive
   (low pairwise lemma overlap);
3. clause lengths are not mechanically identical (char-length variance > ~30%, or a
   monotonic ascending/descending climax gradient);
4. the run is capped by a synthesis/turn sentence within 1–2 sentences.

Otherwise it stays a cadence defect (the "This is… This is…" tic). The sample's
"The setup… The language… The witness…" run is exempted and credited.

### Register-conditioned modifier corridor

Replaces the global 0.25 modifier budget. Starting bands, calibrated to corpus
percentiles:

| Register | Modifier budget | Cadence corridor | Concreteness target | Overt devices/para |
|---|---|---|---|---|
| Technical-exposition | tight (~<0.20) | narrow (tech band) | low–moderate | 0–1 |
| Narrative-editorial | relaxed (~<0.30) | wide (editorial band) | high | 1 |
| Polemic | moderate | wide, sharp turns | moderate–high | 1 (stance-driven) |

The **accuracy floor** (atomicity, hedging, epistemic precision, agentless-passive)
is identical across registers — only texture dials move.

## Component 3 — Positive signals (`liveliness-signals`, advisory in phase 1)

Each emits a paragraph-level score + JSON; none hard-fails in phase 1.

1. **Cadence corridor** (deterministic) — sentence-length distribution vs the
   register percentile band; rewards in-band variety, flags both metronomic and
   erratic. CV is one component.
2. **Verb-energy** (spaCy) — density of light-verb + event-noun constructions
   (make/have/give/take/do/conduct/perform + event noun), *not* raw `-tion`
   counts; domain allow-list from the profile.
3. **Concrete-anchor** (deterministic + Brysbaert lexicon) — ratio of
   concreteness-≥4.0 nouns + bonus for a concrete noun reused as an explanatory
   anchor across sentences; register-conditioned minimum.
4. **Subject→verb distance** (spaCy) — `nsubj`→`ROOT` token distance, advisory
   penalty > 7 (Gopen–Swan cognitive load).
5. **Curiosity setup-payoff** (deterministic/spaCy) — a setup frame followed by a
   causal/demonstrative payoff within 1–2 sentences; thresholded by density, not
   keyword presence.
6. **Analogy-mapping** (deterministic v1; embedding v2) — a base-domain frame
   outside the topic lexicon mapped across ≥2 clauses; v2 adds domain vector-offset.
7. **Novelty-continuity** (deterministic) — adjacent-sentence content-lemma overlap
   inside a corpus-calibrated corridor. **Doubles as the anti-gaming coherence
   check coupled to cadence** — a disconnected short punchline fails it.
8. **Worked-case presence** (deterministic) — a worked example / contrast pair /
   counterexample for abstract thesis paragraphs; passage-type routed (required in
   "explain", optional in "define").

## Component 4 — Generation v2 (`triadic-voice-v2`)

- **Register router** classifies the prompt → technical / narrative / polemic,
  selecting the dial set.
- **Chassis library (6 archetypes):** Objection→decomposition→verdict;
  Definition-correction→worked-case→consequence;
  Concrete-scene→abstraction→boundary-condition;
  False-slogan→causal-account→exact-replacement (Report 1); Inverted Funnel
  (Russell-open) and Feynman Sandwich (Feynman-open/close) (Report 2).
- **Profile-driven targets** injected into the generation prompt (sentence-length
  bands, discourse-marker/direct-address rates, example spacing) — statistical
  bounds, since LLMs respond to distributions better than to counts.
- **Retrieval** by tuple `{register, move, stance, cadence pattern, device family}`.
- **Per-beat plan-then-adapt loop** (RePA-grounded): plan chassis beats → draft beat
  → self-check vs floor + signals → adapt.
- **Anti-copy alarm:** lemma/POS-trigram overlap vs corpus + taboo verbatim list.

## Component 5 — Evaluation: the 20×20 final test (`voice-eval`)

1. **Prompt set:** 20 prompts stratified ~7/7/6 across the three registers.
2. **Generate:** 20 via `triadic-voice` (v1) + 20 via `triadic-voice-v2`, in-session.
3. **Gate:** all 40 must clear the `russellian-style` **v1** floor (equal
   grounding); regenerate any failure.
4. **Metrics:** score all 40 on the 8 signals → per-signal mean delta (v2−v1),
   overall and per register.
5. **Blind pairwise judge** (in-session; the self-preference bias cancels):
   order-swapped (each pair judged twice), length-matched, CoT rationale;
   forced-choice ("which would you keep" / "which made you want the next sentence
   more") + ordinal momentum / clarity / voice-authority / readability /
   **trustworthiness**. Win-rate with CIs.
6. **Formula-drift:** TF-IDF structural cosine on first/last sentences +
   opening-POS + analogy-family reuse, within each arm's 20.
7. **Report:** deltas + win-rate + drift + flagged examples.

**Success:** v2 stays floor-clean, scores higher on the positive signals, wins
>50% pairwise with trustworthiness not worse, and shows lower drift.

## Component 6 — Signal graduation protocol (advisory → gate)

No positive signal becomes a hard gate on the 20×20 alone. Graduation requires the
roadmap's human study (≥50–60 prompts, 12–15 mixed raters, blind A/B): inter-rater
reliability (Fleiss κ / Krippendorff α); a metric graduates only if it shows a
moderate positive Spearman correlation with bootstrap CI excluding zero (Pearson
r > 0.6 secondary) against the targeted human dimension, and never if it hurts
trustworthiness. The 20×20 is the in-session proxy; the human study is the real
gate. AI-detector scores never gate.

## Testing, error handling, regression set

- **Device challenge / regression set:** deliberate anaphora (the sample artifact =
  item 1), analogies without markers, curiosity without question marks,
  technical-but-vivid-via-verbs, dense Russell closes. Every linter change must pass
  it before promotion — a rule that would have flattened the sample is not ready.
- **Graceful degradation:** missing Brysbaert lexicon / spaCy model → explicit
  `WARN` row, never a silent skip (fixes the suite's old catch-all-swallow).
- **TDD per repo convention:** failing test → minimal impl → commit; no live LLM in
  tests (stub `llm_call`); append-only fixtures with `tmp_path`.
- **Vendored assets:** Brysbaert concreteness norms in `liveliness-signals/assets/`;
  `en_core_web_sm` required; venvs on Python 3.14.

## Risks (from the reports, mitigations folded in)

| Risk | Mitigation |
|---|---|
| Purple prose by proxy optimization | reward mapped frames not image tokens; keep modifier budget + ≤1 overt device/para |
| Momentum overpowering accuracy | floor + preserve-argument stay hard; positives advisory until validated |
| Gimmick fatigue across a book | chassis diversification + formula-drift monitor |
| Reward hacking | couple cadence with novelty-continuity coherence; human-correlation gate before promotion |
| Corpus overfit / copying | retrieve by move/cadence; n-gram overlap alarm; taboo verbatim list |
| Miscalibrated linters re-suppressing style | device challenge set is a hard regression gate |

## Out of scope / next step

This design defines the v2 architecture and the 20×20 acceptance test. The
implementation is a separate effort planned via the writing-plans skill, scoped as
per-component TDD waves (profile → floor ruleset → signals → generation → eval),
each citing the OpenSpec REQ IDs. The full human-study harness (item 7) is built but
its raters/run are a later activity; the 20×20 is the in-session acceptance gate.
