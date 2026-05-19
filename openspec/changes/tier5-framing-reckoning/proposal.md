# Change: tier5-framing-reckoning

**Tier:** 5 of 5 (Phase S)
**Branch:** `plan/tier5-metta-runtime`
**Depends on:** `tier5-metta-backend` (Phase O), `tier5-edn-metta-bijection` (Phase P), `tier5-embedding-sidecar` (Phase Q).

## Why

The external analysis comparing this framework to MeTTa / Hyperon / Atomspace
identified a real and damaging drift: the framework's promotional claims have
run ahead of its implementation. Pre-Tier-5 the docs called the
"atomspace conventions" MeTTa-style, which is honest if a reader parses
"shaped like MeTTa" — but most readers parse it as "MeTTa, full stop". The
result is an expectation gap that the runtime cannot meet.

Tiers 1-4 hardened the framework around EDN-on-disk + Z3 + Cozo + egg. Tier 5
Phase O lands a real embedded MeTTa interpreter via the hyperon-experimental
crate (alpha). Phase P lands an EDN↔MeTTa bijection plus Atomspace dedup.
Phase Q lands an embedding sidecar. None of that work removes the drift
problem on its own — it adds new capabilities that the docs must now
distinguish from the older MeTTa-shaped (but not MeTTa-runtime) parts of
the surface.

The framework has done a real thing. The docs need to reckon with it
honestly: name what's runtime-grounded after Tier 5, name what stays
MeTTa-shaped (EDN, defrule, `:backend :z3` / `:cozo`), and explicitly
retract any earlier sentence that implied "the framework runs MeTTa"
without the qualifier.

## What

- Ship `docs/concepts/metta-runtime-grounded-vs-shaped.md` (~150 lines)
  as the canonical distinction reference.
- Update `skills/neurosym-forge/SKILL.md`: name the hyperon-experimental
  crate version + its alpha status, link the new doc near the top, retire
  pre-Tier-5 sentences that overstated the integration.
- Add a `defconstraint :backend :metta` row to `SUPPORT_MATRIX.md`,
  mirroring Phase O's REQ-METTA-045.
- Rewrite `skills/neurosym-forge/references/metta-idioms.md` to add a
  third section "what we now embed at runtime" alongside the existing
  "what we borrow" / "what we don't".
- Grow the drift lint (`tests/test_support_matrix.py`) to catch future
  promotional drift specifically on `:metta` rows (words like
  "production" / "stable" alongside the alpha-tagged row).
- Provide a deprecation runbook at
  `docs/operations/deprecate-metta-backend.md` for the day
  hyperon-experimental's API changes incompatibly.
- Add a `:metta` row to `docs/booklogic-dsl-reference.md` §2.5 with the
  `(alpha)` qualifier.

## Capabilities touched

- `booklogic-dsl` — MODIFY (REQ-BOOKLOGIC-060..066).

## Implementation notes

See `docs/plans/2026-05-19-tier5-metta-runtime.md`, Phase S.

## Acceptance

- New concepts doc exists and is linked from SKILL.md.
- SKILL.md, SUPPORT_MATRIX.md, references/metta-idioms.md, and
  docs/booklogic-dsl-reference.md §2.5 all carry the `(alpha)`
  qualifier on the MeTTa backend.
- Drift lint catches the test phrase `":backend :metta is
  production-ready"` and fails.
- Deprecation runbook present.
