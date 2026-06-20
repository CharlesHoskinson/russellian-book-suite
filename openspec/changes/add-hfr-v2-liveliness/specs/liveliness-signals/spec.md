# Spec delta — liveliness-signals

Capability: `LIVE` (liveliness-signals)
Delta against `openspec/specs/liveliness-signals/spec.md` (new capability; all ADD).

## ADD REQ-LIVE-001 — Ubiquitous

The liveliness-signals skill shall provide a corpus profiler that runs offline over
the Hoskinson corpus (the 57 curated paragraphs and cleaned transcripts) and emits
`assets/hoskinson-style-profile.json` containing statistics only — per-register
sentence-length percentile corridors and coefficient of variation, first-word and
discourse-marker distributions, direct-address rate, short-to-long sentence ratio,
mean inter-example spacing, mean Brysbaert noun concreteness, light-verb-construction
rate, and a domain noun allow-list — and no verbatim source prose.

## ADD REQ-LIVE-002 — Event-driven

When the profiler runs over a fixed corpus input, it shall emit the profile
deterministically and shall partition every statistic by register
(technical-exposition, narrative-editorial, polemic).

## ADD REQ-LIVE-003 — Ubiquitous

The skill shall provide eight advisory paragraph-level scorers: cadence corridor,
verb-energy, concrete-anchor, subject-to-verb distance, curiosity setup-payoff,
analogy-mapping, novelty-continuity, and worked-case presence. Each shall emit a
paragraph-level score and JSON findings.

## ADD REQ-LIVE-004 — State-driven

While running in phase 1, the positive signals shall be advisory: they shall not
gate, fail, or block any pipeline stage.

## ADD REQ-LIVE-005 — Ubiquitous

The cadence-corridor scorer shall compare the passage's sentence-length distribution
to the register percentile corridor from the profile, flagging both metronomic
(below corridor) and erratic (above corridor) prose, and shall not rely on a single
coefficient of variation as the sole criterion.

## ADD REQ-LIVE-006 — Ubiquitous

The verb-energy scorer shall measure the density of light-verb-plus-event-noun
constructions (a semantically light verb such as make, have, give, take, do,
conduct, or perform governing an event nominalization) and shall not penalize
nominalizations identified by suffix alone. It shall exempt nouns on the profile
domain allow-list.

## ADD REQ-LIVE-007 — Ubiquitous

The concrete-anchor scorer shall compute the ratio of nouns whose Brysbaert
concreteness rating is at or above 4.0 to total nouns, shall add a bonus when a
high-concreteness noun is reused as an explanatory anchor across adjacent sentences,
and shall apply a register-conditioned minimum.

## ADD REQ-LIVE-008 — Ubiquitous

The curiosity setup-payoff scorer shall detect a setup frame followed within one to
two sentences by a causal or demonstrative payoff, and shall score by setup-payoff
density rather than by the presence of literal marker keywords or question marks.

## ADD REQ-LIVE-009 — Ubiquitous

The analogy-mapping scorer shall detect a base-domain frame outside the topic lexicon
whose relations are mapped across at least two clauses or sentences, and shall not
rely on literal analogy marker words. Its v2 mode may use offline embeddings to
detect a cross-domain cluster; its v1 mode shall be deterministic.

## ADD REQ-LIVE-010 — Ubiquitous

The novelty-continuity scorer shall measure adjacent-sentence content-lemma overlap
against a corpus-calibrated corridor (rewarding overlap that is neither near-zero nor
near-identical) and shall serve as the coherence check that a disconnected
short-sentence punchline fails.

## ADD REQ-LIVE-011 — Optional feature

Where a passage is routed as an "explain" passage type, the worked-case scorer shall
require a worked example, contrast pair, or counterexample frame; where it is routed
as "define", the worked case shall be optional.

## ADD REQ-LIVE-012 — Unwanted behaviour

If a required static resource (the Brysbaert lexicon or the spaCy `en_core_web_sm`
model) is absent, then the affected scorer shall emit an explicit WARN finding and
shall not silently pass.

## ADD REQ-LIVE-013 — Ubiquitous

The skill shall maintain a device challenge regression set whose first item is the
trust-decomposition sample artifact, also containing deliberate anaphora, analogies
without marker words, curiosity without question marks, technical prose vivid through
verbs, and dense Russell-style closes. No linter change shall promote if it regresses
this set.

## ADD REQ-LIVE-014 — Ubiquitous

The profiler shall be network-free; fetching of any external resource shall be a
separate documented step performed through scrapling-fetch.
