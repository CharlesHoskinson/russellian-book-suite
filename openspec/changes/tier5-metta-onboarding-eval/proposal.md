# Change: tier5-metta-onboarding-eval

**Tier:** 5 of 5 (Phase T)
**Branch:** `plan/tier5-metta-runtime`
**Depends on:** `tier5-metta-backend` (Phase O), `tier5-framing-reckoning` (Phase S),
and the existing Phase N onboarding bench (REQ-EVAL-050..055).

## Why

Phase N shipped an automated onboarding benchmark: a fresh agent is given
only the doc bundle, handed a one-paragraph domain prompt, and measured
on whether it can reach `make extract` and `make ci` green. Three
domains cover the pre-Tier-5 surface.

Tier 5 adds a new backend (`:backend :metta`) and a real MeTTa runtime.
The onboarding question for that backend is empirically distinct from
the Phase N domains: can a fresh agent, reading only the post-Tier-5
docs, wire a verifier that actually uses `:backend :metta`? Or do the
docs underdescribe when `:metta` is the right tool, leaving agents to
translate the constraint into `:z3` instead?

The framing-reckoning change (Phase S) makes the docs honest about what
the `:metta` backend is. This change measures whether the honest docs
are also actionable.

## What

- Author a fourth domain prompt at
  `skills/neurosym-forge/eval/prompts/grandparent-metta.md` describing
  a 2-rule MeTTa-runtime verifier (`Parent` facts plus a
  `(= (Grandparent $x $z) (, (Parent $x $y) (Parent $y $z)))` rule).
- Extend the onboarding-bench harness to accept the new domain.
- Add a `metta_backend_used: bool` column to the per-run CSV.
- Define SUCCESS as `make ci PASS` AND `:backend :metta` in
  `rules/constraints.edn` AND `:metta-results` in the verdict surface.
- Define `SUCCESS_WITHOUT_METTA` as a flagged data point (not a hard
  failure) for runs that pass `make ci` by translating to `:z3`.
- Grow the aggregator report with a "MeTTa-backend-uptake" section.

## Capabilities touched

- `framework-eval` — MODIFY (extends Phase M/N with REQ-EVAL-060..065).

## Implementation notes

See `docs/plans/2026-05-19-tier5-metta-runtime.md`, Phase T.

## Acceptance

- The grandparent prompt file exists with the documented rule shape.
- `onboarding-bench.py --domain grandparent-metta` runs end-to-end and
  produces a CSV row including the `metta_backend_used` column.
- The aggregator report grows the "MeTTa-backend-uptake" section
  reporting % `:metta` used / % bypassed to `:z3` / % failed.
- Stub-backend runs deterministically produce `STUB_SUCCESS`.
