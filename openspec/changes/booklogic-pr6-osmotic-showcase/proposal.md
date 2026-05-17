# Change: booklogic-pr6-osmotic-showcase

**Sprint:** 5 of 5 (final)
**Branch:** `feat/booklogic-pr6`
**GitHub Milestone:** `booklogic-pr6-osmotic-showcase`
**On merge:** publish `v0.4.0` GitHub Release.

## Why

The mission promises a non-book domain to prove BookLogic is reusable
beyond the Bermuda manual. None exists. Without a chemistry-domain
showcase, the "generic DSL" claim is unsupported.

## What

- Greenfield `verifiers/osmotic_pressure/` scaffolded entirely via the
  BookLogic compiler (no hand-edits beyond what BookLogic generates).
- `rules/sorts.edn`, `predicates.edn`, `lifts.edn`, `constraints.edn`
  encoding the van 't Hoff equation `π = i·M·R·T` with `~=` 3% tolerance.
- Two fixture ledgers:
  - `claims_clean.jsonl` — i=2, M=0.154, T=298.15, π=780202.5 → expect `:sat`
  - `claims_doctored.jsonl` — i=1, same M/T/π → expect `:unsat` with the i=1
    claim id in the unsat core
- New `osmotic-pressure-smoke` CI job.
- On merge: publish `v0.4.0`.

## Capabilities touched

- `osmotic-pressure-verifier` — ADD (this capability is created by this change)

## Implementation notes

See `docs/plans/2026-05-17-booklogic-pr6.md` (8 phases).

## Acceptance

- Scaffolded project builds with zero hand-edits
- Both fixture verdicts match expected
- `~=` codegen exercised end-to-end
- CI smoke job is green
- All REQ IDs added are test-covered
