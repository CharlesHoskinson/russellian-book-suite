# Change: tier5-scale-corpus

**Tier:** 5 of 5 (scale + author-facing tier)
**Branch:** `plan/tier5-scale-author`
**Depends on:** Tier 1-4 landed (binding-schema, encoder-extensions,
cozo-runtime, egg-promotion, cross-OS CI matrix)

## Why

"General-purpose" was a hypothesis backed by three verifiers
authored against ~100-claim corpora (bermuda ~100, osmotic ~5,
epidemiology ~6). None of the three exercised real-corpus
scale. A framework that handles 100 claims in 30 seconds may
or may not handle 1000 claims in 5 minutes — and the failure
modes that surface only at scale (memory ceilings, regex
runtime, Cozo plan blow-ups, embedding overhead) are exactly
the ones the existing eval bench cannot see.

Phase M (eval-third-verifier) established the build-log
discipline at 1× scale. Phase O applies that same discipline
at 10× scale: build a fourth verifier against a real-corpus
1000+ claim source, log every gap, and produce a scale-eval
report that names the framework's actual scaling profile —
not its hoped-for one.

## What

- A fourth verifier under `verifiers/adsc-clinical/` ingesting
  1000+ claims from `~/OneDrive/Desktop/stemCells/ADSC_Complete_Report.md`
  (4816 lines of clinical evidence, trial-sized claims with
  cross-paragraph consistency obligations).
- The standard project structure (rules/booklogic, fixtures,
  rust-verifier, cljs-orchestrator, scripts, tests, Makefile)
  with at least 5 clean + 3 doctored fixtures, each doctored
  fixture targeting a distinct defect class.
- A scale-build log at
  `docs/eval/2026-05-19-scale-corpus-build-log.md` recording
  every framework gap surfaced only at 1000-claim scale, with
  tier-link.
- A scale-eval report at
  `docs/eval/2026-05-19-scale-eval-report.md` synthesising
  throughput (claims-per-minute), peak RSS, defect-detection
  rate on doctored fixtures, false-positive rate on clean
  fixtures, and the framework's actual scaling profile.
- At least one cross-paragraph consistency constraint
  exercising Phase R's `:scope :corpus` work where the corpus
  references the same trial in two sections.

## Capabilities touched

- `framework-eval` — EXTEND (Phase M added REQ-EVAL-040..047
  at 1× scale; Phase O extends with REQ-CORPUS-040..046 at
  10× scale on a real corpus)

## Implementation notes

See `docs/plans/2026-05-19-tier5-scale-author.md`, Phase O.

## Acceptance

- 7 REQ-CORPUS IDs ship in `specs/framework-eval/spec.md`.
- `verifiers/adsc-clinical/` builds clean from `make ci` with
  5 clean and 3 doctored fixtures over 1000+ claims.
- The build log enumerates every scale-only gap with one of
  `fixed`, `workaround`, `deferred-to-issue-N`.
- The scale-eval report names throughput, peak RSS, detection
  rate, false-positive rate, and the scaling-cliff phases.
