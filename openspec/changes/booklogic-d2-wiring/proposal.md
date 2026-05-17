# Change: booklogic-d2-wiring

**Sprint:** 2 of 5
**Branch:** `feat/booklogic-d2-wiring`
**GitHub Milestone:** `booklogic-d2-wiring`

## Why

PR-2 of the v0.4 mission shipped `skills/book-knowledge/scripts/export_symbolic_trace.py`,
which emits `analysis/ingest-trace.edn` — a symbolic event stream of
ingestion events. But no verifier consumes it. `verifiers/bermuda/scripts/run_verification.py`
still reads `claims/ledger.jsonl` directly, defeating the purpose of the
trace artifact.

D2 of the mission spec is therefore half-done. This change closes it:
the Bermuda verifier reads the trace when present, falls back to the
legacy ledger when not, and the CLJS `translate` accepts either claim-list
or event-stream input.

## What

- `run_verification.py` Phase-1 reads `analysis/ingest-trace.edn` if present,
  falls back to `claims/ledger.jsonl`.
- CLJS `bermuda.core.translate` dispatches on event-head when given the
  event-stream shape, preserving the legacy claim-list path.
- One integration test synthesises a trace and asserts the verifier emits
  the expected atoms.

## Capabilities touched

- `ingest-trace` — ADD requirements for the consume-side contract
- `cljs-orchestrator` — ADD requirement for event-aware `translate`

## Implementation notes

See `docs/plans/2026-05-17-booklogic-d2-wiring.md` (5 phases, 11 tasks).

## Acceptance

- `run_verification.py` exits 0 against a fresh workspace that has
  `analysis/ingest-trace.edn` but no `claims/ledger.jsonl`
- Existing legacy-path tests still pass
- The Bermuda smoke CI pipeline is still green
- All REQ IDs added are test-covered
