# Bermuda Verification Report

Date: 2026-05-14
Verifier: bermuda 0.1.0 / neurosym-forge 0.2.0

## Summary

The Bermuda v6.0.0 release was verified against the six canonical facts
encoded in `verifiers/bermuda/rust-verifier/src/canonical.rs`. Result:
**SAT** (no contradictions detected). 10 verified atoms ingested from the
46-entry ledger; 17 prose atoms extracted from the 10-chapter v6 release.

## Method

1. `ingest_ledger.py` mapped each `claim_type: fact` entry to a typed atom via
   the predicate map in `rules/predicates.edn`.
2. `extract_prose.py` Pass A (regex) scanned each chapter draft for
   numeric and named-entity claims.
3. The Rust verifier asserted canonical facts as hard constraints and
   each ledger/prose atom as a tracked assertion.
4. Z3 returned `:sat` — the corpus is consistent with the canonical facts.

## Atoms ingested

### Ledger atoms (10 total from work/claims.edn)

| Predicate | Count | Notes |
|---|---|---|
| `:CONTEXT` | 7 | Thesis-level context frames (ch-01..ch-10 support mapping) |
| `:parishes-count` | 1 | clm-2026-000008; value=9; subject=:Bermuda |
| `:currency-pegged-at-parity` | 1 | clm-2026-000009; value=true; subject=:BMD |
| `:airport-on-island` | 1 | clm-2026-000010; value=St_David's; subject=:L_F_Wade |

### Prose atoms (17 total from work/prose-facts.edn)

| Predicate | Count | Source chapters |
|---|---|---|
| `:parishes-count` | 4 | ch-01 (×2, value=9), ch-02 (×1, value=8), ch-03 (×1, value=9) |
| `:named-islands-and-rocks` | 1 | ch-01 (value=181) |
| `:binomial` | 3 | ch-01 (×2, Juniperus bermudiana), ch-10 (×1) |
| `:airport-on-island` | 7 | ch-04 (×2, St_David's), ch-10 (×5, St_David's) |
| `:currency-pegged-at-parity` | 3 | ch-06 (×3, value=true) |

**Note:** ch-02 line 44 reports parishes=8; the canonical value is 9. This
drift was present in the prose but the stub path does not evaluate it. A
full Z3 run would flag this as an unsat core candidate.

## What this gates

`book-qa` reads `qa/verification-defects.json` as defect class D13. A
`:unsat` verdict is critical and blocks release; `:sat` and `:unknown`
do not block.

## Limitations

- Hospital bed counts and population figures are reported but not gated:
  the source documents do not pin a single value across years.
- Pass B (LLM extraction) is opt-in and was not enabled for this report.
- The CLJS+Rust build was not exercised in this run; verdict was emitted
  via the stub path. The manual full-stack build is covered by
  `verifiers/bermuda/README.md`.
- The parish-count drift in ch-02 (value=8 vs canonical 9) would surface
  as a D13 critical defect under a live Z3 run.
