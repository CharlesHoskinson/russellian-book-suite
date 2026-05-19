# Change: tier5-confidence-propagation

**Tier:** 5 of 5 (scale + author-facing tier)
**Branch:** `plan/tier5-scale-author`
**Depends on:** Tier 1-4 landed; co-runs with tier5-cross-chapter

## Why

Every atom in `claims.edn` already carries a `:confidence <float>`
field (`verifiers/osmotic_pressure/scripts/ingest_ledger.py:167`),
populated by upstream extractors. Today that field is stored at ingest
and never read. The verdict treats every defect at full severity,
which makes the framework loud about extraction noise: a defect with
an unsat core composed entirely of `:confidence 0.3` claims is
indistinguishable from a defect grounded in `:confidence 0.95` claims,
and authors get the same red banner for both.

The fix is mechanical. Propagate confidence from atoms to defect
explanations: a defect's confidence is the minimum confidence of the
atoms in its unsat core (weakest-link); a verdict's confidence is the
geometric mean of its defects' confidences. Below a configurable
threshold a defect downgrades from its declared severity to
`:advisory`. The framework stays loud about high-confidence
violations, quieter about low-confidence ones.

## What

- Every defect's verdict entry gains `:defect-confidence` — the min
  confidence of its unsat-core atoms.
- The verdict's top-level gains `:verdict-confidence` — the geometric
  mean across defects.
- Defects whose chain is fully below `VERIFIER_CONFIDENCE_THRESHOLD`
  (default 0.5) downgrade to `:severity :advisory` and surface in a
  separate `:advisory-defects` array in the QA JSON.
- Missing or out-of-range `:confidence` fails at ingest with a clear
  per-claim error.

## Capabilities touched

- `verifier-build` — EXTEND (adds REQ-CONFIDENCE-040..045)

## Implementation notes

See `docs/plans/2026-05-19-tier5-scale-author.md`, Phase S.

## Acceptance

- 6 REQ-CONFIDENCE IDs ship in `specs/verifier-build/spec.md`.
- A unit test exercises high-confidence chain (severity preserved),
  mixed chain (defect-confidence equals min), and below-threshold
  chain (downgraded to `:advisory`).
- `verdict_to_qa.py` surfaces advisory-downgraded defects under a
  separate `advisory_defects` array.
- An out-of-range `:confidence` fails at ingest naming the claim id.
