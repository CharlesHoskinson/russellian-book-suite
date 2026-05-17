# Capability: ingest-trace

The symbolic event stream exported by `book-knowledge` and consumed by
`verifiers/bermuda` as the Phase-1 input to verification. Replaces the
direct read of `claims/ledger.jsonl` with a typed event sequence
(`source/ingested`, `claim/proposed`, `claim/verified`, `atom/emitted`) at
`<workspace>/analysis/ingest-trace.edn`.

Spec deltas accumulate here as sprints merge. Sprint
booklogic-d2-wiring adds REQs.

## Requirements

_(none yet)_
