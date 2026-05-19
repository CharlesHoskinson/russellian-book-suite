# Design: tier5-scale-corpus

## Corpus choice

Three candidate corpora were considered. The comparison table:

| Corpus                | Size            | Claim shape                | Cross-paragraph? | Why it tests the framework         |
|-----------------------|-----------------|----------------------------|------------------|------------------------------------|
| ADSC clinical report  | 4816 lines, ~820KB | trial-sized: `n=X, p<Y, treatment Z` | yes (same trial cited in two sections) | quantitative + cross-paragraph at scale |
| epochpoet (LaTeX)     | one protocol paper | protocol-spec: `parameter P set to V` | mostly within-section | math-heavy but small |
| sevenlayer ZK book    | book-length | exposition + algebra | yes, but mostly informal | broad but few quantitative claims |

**Decision: ADSC clinical.** Three reasons:

1. **Quantitative claim density.** Clinical evidence is
   structured around trial parameters (cohort size, p-value,
   confidence interval, treatment arm) — every paragraph
   yields multiple typed atoms, so 1000+ claims is reachable
   without forcing the corpus.
2. **Cross-paragraph consistency.** The same trial is
   referenced in the executive summary and again in the
   detailed evidence section. The verifier can therefore
   exercise `:scope :corpus` consistency (Phase R) on a real
   pair, not a synthetic one.
3. **Real-world regulatory framing.** The corpus has
   regulatory consequences for the author (Charles); the eval
   produces immediate value beyond framework testing.

The other two corpora remain available for follow-up phases
(epochpoet is the natural Phase T publication-bridge target;
sevenlayer is Phase S confidence-propagation territory).

## Verifier structure

Standard project layout cloned from `verifiers/epidemiology/`:

```
verifiers/adsc-clinical/
├── Makefile
├── README.md
├── SKILL.md
├── cljs-orchestrator/
├── deps.edn
├── fixtures/
│   ├── claims_clean_safety_arm.jsonl
│   ├── claims_clean_efficacy_arm.jsonl
│   ├── claims_clean_dose_response.jsonl
│   ├── claims_clean_long_term_followup.jsonl
│   ├── claims_clean_combination_therapy.jsonl
│   ├── claims_doctored_inconsistent_cohort_size.jsonl
│   ├── claims_doctored_pvalue_drift.jsonl
│   └── claims_doctored_misquoted_endpoint.jsonl
├── nbb.edn
├── package.json
├── pyproject.toml
├── rules/booklogic/
├── rust-verifier/
├── scripts/
└── tests/
```

Predicate set (illustrative):

```edn
(defpredicate :cohort-size         [:trial] :int)
(defpredicate :p-value             [:trial :endpoint] :real)
(defpredicate :confidence-interval [:trial :endpoint] :real)
(defpredicate :treatment-arm       [:trial] :keyword)
(defpredicate :primary-endpoint    [:trial] :keyword)
(defpredicate :follow-up-months    [:trial] :int)
(defpredicate :adverse-event-rate  [:trial :grade] :real)
(defpredicate :dose-mg-per-kg      [:trial] :real)
```

Eight predicates ensures the by-predicate distribution is
non-trivial (REQ-CORPUS-041).

## Build-log structure

`docs/eval/2026-05-19-scale-corpus-build-log.md` follows the
same chronological-diary shape as Phase M's build log. Each
entry:

```
### 2026-05-19 HH:MM — <one-sentence roadblock>

**Symptom:** what the build did at 1000+ scale that did not
appear at 100-claim scale
**Root cause:** what was actually going on
**Resolution:** one of
  - `fixed` — patched the framework
  - `workaround` — wrote around it; issue #NNN tracks the
    follow-up
  - `deferred-to-issue-N` — known limitation
**Scale-impact:** at what claim count the issue appeared
**Tier link:** if applicable, the OpenSpec change that closes
it
```

Examples of plausible scale-only entries:

- Cozo plan blow-up on a join over 1000 atoms → workaround:
  add index on `:trial`; file as Tier 4 enhancement candidate.
- Regex evaluator's `re.search` re-compilation per claim
  burned 12 seconds → fixed: pre-compile pattern at lift load.
- `:cozo-defects` verdict field grew 3MB; book-qa consumer
  could not load it → file as compaction follow-up.

## Scale-eval report shape

`docs/eval/2026-05-19-scale-eval-report.md` is short (2-3
pages) and lists six metrics:

```
| Metric                          | Value           | Method      |
|---------------------------------|-----------------|-------------|
| Claims ingested                 | <int>           | wc -l       |
| Claims-per-minute throughput    | <int>           | time make ci|
| Peak RSS (MB)                   | <int>           | /usr/bin/time -v |
| Defect detection rate           | <fraction>      | doctored ÷ surfaced |
| False-positive rate             | <fraction>      | clean false-fires ÷ total clean |
| Phase with longest runtime      | <phase name>    | profile output |
```

The "scaling profile" section names which phases hit a
performance cliff and which scaled linearly. This is the
artefact future tiers measure against.

## Profiling discipline

REQ-CORPUS-044 demands profiling output for any phase >5
minutes. The default profiler is `py-spy record -o
work/profile-<phase>.svg`. The Rust verifier path uses
`cargo flamegraph`. Profiling output lives under
`docs/eval/profiles/` and is linked from the build log.

## Why not bundle this with Phase P (LLM lifts)?

LLM lifts (Phase P) is an ergonomics fix; it does not change
the scale story unless the cache hits dominate. Phase O
establishes the scale baseline with regex lifts so Phase P's
follow-up eval can compare apples-to-apples.

## Why ADSC and not a Cardano-internal corpus?

Cardano-internal docs (paper A, paper B) are the natural
follow-up but their claim shape is closer to bermuda
(entity-counts) and osmotic (one-equation). ADSC's clinical
shape exercises a constraint family the framework has not
seen before — same logic as Phase M's epidemiology choice.
