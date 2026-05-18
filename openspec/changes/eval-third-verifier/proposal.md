# Change: eval-third-verifier

**Track:** Usefulness verification (1 of 2)
**Branch:** `eval/third-verifier`
**Depends on:** Tier 1 docs landed (tier1-references-docs, tier1-binding-schema, tier1-solver-timeout, tier1-fact-extraction-preview)

## Why

The framework calls itself general-purpose, but only two verifiers ship today:
`verifiers/bermuda/` (entity-counts, `:int` predicates) and `verifiers/osmotic_pressure/`
(one-equation arithmetic, `:real` predicates with `approx=`). Both were authored
by the same person who wrote the framework. The "general-purpose" claim is
therefore unverified — every example exercising the framework was built by the
person who knew where the rough edges were before sitting down.

A third domain verifier, built from scratch along an axis the existing two do
NOT exercise (multi-equation constraint sets, cross-document consistency,
threshold inequalities), is the minimum bar for the framework being general-purpose
rather than merely "the framework that produced bermuda and osmotic". The act
of building the third verifier is the evaluation: every gap that ONLY shows up
when the author is not bermuda/osmotic-trained surfaces as a build-log entry.

The framework today is honest about its rough edges in `SUPPORT_MATRIX.md`
(stub egg, DROP cozo backend on constraints, validation-only defsort/defpredicate
codegen). What is NOT documented is which of those rough edges block a working
third domain — and which are merely cosmetic. The build log answers that.

## What

- Build a third verifier under `verifiers/<domain>/` (epidemiology — R0 thresholds
  and herd immunity; chosen for the inequality predicates and cross-disease
  consistency it forces).
- Ship the verifier with the standard project structure (rules/booklogic,
  fixtures, rust-verifier, cljs-orchestrator, scripts, tests, Makefile) and
  end-to-end `make ci` green with 3 clean + 2 doctored fixtures.
- Keep an honest build log at `docs/eval/2026-05-XX-third-verifier-build-log.md`:
  every roadblock, every workaround, every framework gap. The log is the artefact;
  the verifier is the medium that produced it.
- Synthesise a final usefulness report at
  `docs/eval/2026-05-XX-framework-usefulness-report.md` distinguishing
  "worked first try" / "needed a workaround" / "still missing".

## Capabilities touched

- `framework-eval` — ADD (new shared capability; eval-onboarding-bench extends it)

## Implementation notes

See `docs/plans/2026-05-18-tier234-and-usefulness.md`, Phase L.

## Acceptance

- `verifiers/<chosen-domain>/` builds clean from `make ci` with 3 clean and
  2 doctored fixtures.
- The doctored fixtures surface defects (no false negatives); the clean
  fixtures surface none (no false positives).
- The build log enumerates every roadblock with one of: `fixed`, `workaround`,
  `deferred-to-tier-N`.
- The usefulness report names which Tier 2-4 changes are gating which gaps.
