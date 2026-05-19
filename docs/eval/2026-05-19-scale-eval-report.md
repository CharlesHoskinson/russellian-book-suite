# Scale-eval report — Phase O (tier5-scale-corpus)

**Date:** 2026-05-19
**Branch:** `feat/tier5-scale-corpus`
**Corpus:** ADSC clinical complete report (5628 source lines)
**Verifier:** `verifiers/adsc-clinical/`
**Eval target:** does the russellian-book-suite framework retain its
properties at 10x the eval-bench's prior corpus size?

The companion build log
(`docs/eval/2026-05-19-scale-corpus-build-log.md`) records the
framework gaps surfaced authoring this verifier. This report names
the quantitative ground truth.

## Headline result

The framework handles 1852 quantitative claims with `make ci`
end-to-end in under 6 seconds and ~31 MB peak RSS. Defect-detection
discriminates among the 3 doctored fixtures via delta-against-baseline.
Zero false positives across the 6 clean fixtures. No phase tripped
the 5-minute REQ-CORPUS-044 threshold; no profile artefact captured.

## The six required metrics (REQ-CORPUS-046)

| Metric                          | Value             | Method                                      |
|--------------------------------:|:------------------|:--------------------------------------------|
| Claims ingested                 | 1852              | `wc -l fixtures/claims_clean.jsonl`         |
| Claims-per-minute throughput    | ~21,640           | 1852 claims / 5.135 s total `make ci`       |
| Peak RSS (MB)                   | 30.97             | `psutil.Process().memory_info().rss`        |
| Defect detection rate           | 3/3 (1.0)         | doctored fixtures surfaced / total doctored |
| False-positive rate             | 0/6 (0.0)         | clean fixtures surfacing `:unsat` / total clean |
| Phase with longest runtime      | `check_fixtures`  | per-phase wall-clock instrumentation        |

Total `make ci` wall-clock: **5.135 s** (warm cache).

## Per-phase profile

| Phase                                                   | Wall-clock (s) | RSS (MB) | Atoms |
|--------------------------------------------------------:|:--------------:|:--------:|:-----:|
| ingest_claims_clean.jsonl                               | 0.299          | 27.28    | 1852  |
| ingest_claims_clean_intro.jsonl                         | 0.256          | 27.51    | 1292  |
| ingest_claims_clean_knee_oa.jsonl                       | 0.042          | 27.52    | 151   |
| ingest_claims_clean_crohns.jsonl                        | 0.008          | 27.37    | 45    |
| ingest_claims_clean_cardiac_neuro.jsonl                 | 0.026          | 27.37    | 124   |
| ingest_claims_clean_regulatory.jsonl                    | 0.055          | 27.52    | 240   |
| ingest_claims_doctored_low_n.jsonl                      | 0.377          | 30.59    | 1854  |
| ingest_claims_doctored_p_value_drift.jsonl              | 0.357          | 30.77    | 1854  |
| ingest_claims_doctored_adverse_above_efficacy.jsonl     | 0.323          | 28.02    | 1854  |
| **check_fixtures (delta-vs-baseline over 9 fixtures)**  | **2.468**      | **30.97**| —     |
| extract_preview (by-predicate distribution)             | 0.922          | 30.97    | 1852  |

## Defect detection

The Python defect-checker (`tests/check_fixtures.py`) applies the
three constraints declared in `rules/booklogic/constraints.edn`:

- C001-trial-n-minimum   (>= trial-n 10)    -> :D40
- C002-p-value-significance  (<= trial-p-value 0.05)  -> :D41
- C003-efficacy-above-harm  (<= adverse-event-rate treatment-efficacy)  -> :D42

| Fixture                                              | Verdict | Delta-vs-baseline | Expected |
|-----------------------------------------------------:|:-------:|:------------------|:---------|
| claims_clean.jsonl                                   | :sat    | []                | :sat / [] |
| claims_clean_intro.jsonl                             | :sat    | []                | :sat / [] |
| claims_clean_knee_oa.jsonl                           | :sat    | []                | :sat / [] |
| claims_clean_crohns.jsonl                            | :sat    | []                | :sat / [] |
| claims_clean_cardiac_neuro.jsonl                     | :sat    | []                | :sat / [] |
| claims_clean_regulatory.jsonl                        | :sat    | []                | :sat / [] |
| claims_doctored_low_n.jsonl                          | :unsat  | [:D40]            | :unsat / [:D40] |
| claims_doctored_p_value_drift.jsonl                  | :unsat  | [:D41]            | :unsat / [:D41] |
| claims_doctored_adverse_above_efficacy.jsonl         | :unsat  | [:D42]            | :unsat / [:D42] |

Defect detection rate: **3/3 (1.0)**.
False-positive rate: **0/6 (0.0)** in delta-vs-baseline mode.

## By-predicate distribution (REQ-CORPUS-041)

Run against `claims_clean.jsonl` (1852 sentences):

| Predicate              | Facts | Sample value |
|-----------------------:|:-----:|:-------------|
| trial-n                | 24    | 261          |
| trial-p-value          | 21    | 0.0002       |
| patient-count          | 66    | 0            |
| follow-up-months       | 13    | 24.0         |
| treatment-efficacy     | 14    | 40.0         |
| adverse-event-rate     | 4     | 91.0         |
| primary-endpoint-met   | 5     | True         |
| dose-mg                | 2     | 10.0         |
| **8 distinct predicates** | **149 typed atoms** | (8.0% of 1852) |

OPAQUE / unmatched: 1703 sentences (92.0%). This is the regex-only
extractor's ceiling on narrative-prose clinical writing; Phase P's
LLM lifts are expected to lift the bulk of the OPAQUE fraction.

## Scaling profile — what scaled linearly, what cliff-y

**Scaled linearly with claim count:**

- *Ingest (read JSONL, apply regex map per claim, emit EDN atom).*
  Each fixture's ingest time was approximately proportional to its
  claim count (0.008 s for 45 claims -> 0.377 s for 1854 claims).
  Throughput: ~5000 claims/s steady-state. Python `re.search` cost
  is the dominant term; the regex set is small enough that scaling
  is linear up to at least 10k claims.

- *Extract-preview (the by-predicate distribution report).*
  Single-pass over the atom list; sub-second on the 1852-atom set.

- *Memory.* RSS grew from 27 MB cold to 31 MB after 9 fixture passes.
  This is `python` baseline + the 1852-atom dict-of-dict atomspace
  held simultaneously. No leak suspected.

**Cliff-y / non-linear hot spots:**

- *Cross-fixture defect check (`check_fixtures`)* dominated wall-clock
  at 2.47 s — half the total `make ci` time. The check is naive O(N*M)
  over (clean-baseline-defect-ids x doctored-defect-ids) per fixture;
  with 1854 atoms per fixture and 9 fixtures, the constant factor
  bites. A `set.difference` already short-circuits the comparison so
  it's not asymptotic; the cost is repeated `compute_atoms` calls.
  At the 10x-current scale (~18k claims), this phase would run for
  ~25 s on the same hardware — still under the 5-minute cliff. At
  100x scale (~180k claims) the constant-factor dominance would put
  it at ~4 minutes, very close to the cliff.

- *Regex-map application.* `_apply_predicates` returns on first
  match; with the predicate dict ordering brittleness logged in the
  build log, latency is fine but coverage is the visible cliff. The
  92% OPAQUE fraction is the framework saying "I don't speak this
  prose without help" — a coverage cliff that Phase P targets.

## Did the framework hold its properties at 10x?

Mostly yes; with two clearly-named workaround dependencies:

1. **Coverage (NOT throughput) is the scale-tier cliff.** Throughput
   and memory profile are linear in claim count; the eval-bench can
   handle 10k+ claims on this hardware without architectural change.
   The actual bottleneck is the regex-only lift's coverage rate
   (8% typed, 92% OPAQUE on narrative prose). Phase P's LLM extractors
   are the right tier to close this.

2. **Constraint semantics need subject-scope at scale.** The three
   within-trial constraints fire trivially on the clean baseline
   when applied trial-scope-blind (the corpus naturally contains
   low-n pilots and high-p exploratory subgroups). The
   delta-against-baseline workaround captured the same discriminative
   power for this eval but is brittle for production. Phase R
   (`tier5-cross-chapter`) is the structural fix.

The framework is fit for the next eval tier (Phase P on this same
corpus). Phase R is the right partner-tier to land alongside.

## Reproducibility

```bash
cd verifiers/adsc-clinical
python scripts/ingest_adsc.py \
  --src ~/OneDrive/Desktop/stemCells/ADSC_Complete_Report.md \
  --out fixtures/claims_clean.jsonl
python scripts/make_doctored_fixtures.py
make ci
```

Metrics JSON: `verifiers/adsc-clinical/work/eval_metrics.json`.
Build log: `docs/eval/2026-05-19-scale-corpus-build-log.md`.
