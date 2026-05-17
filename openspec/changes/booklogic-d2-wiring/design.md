# Design: booklogic-d2-wiring

## Architecture pointer

Full TDD-shaped detail at `docs/plans/2026-05-17-booklogic-d2-wiring.md`.

## Key decisions

- The Python side dispatches via path existence (`analysis/ingest-trace.edn`
  takes precedence) rather than a config flag — automatic migration.
- The CLJS side keeps the existing `claim->formula` meander rule unchanged
  as a private helper; a new `event->formula` dispatcher selects it for
  legacy claim-list input.
- A new malli schema `ClaimOrEvent` relaxes the `phases/translate` pre-contract.
- Unknown event heads are opaque (skip), not errors — forward compatibility
  for future event kinds.

## Open questions

None.
