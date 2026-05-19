# Change: tier5-hybrid-query

**Tier:** 5 of 5 (Phase R)
**Branch:** `plan/tier5-metta-runtime`
**Depends on:** `tier5-metta-backend` (Phase O) and `tier5-embedding-sidecar` (Phase Q).

## Why

Phase O wires a real MeTTa runtime via the hyperon-experimental crate; Phase Q
ships an embedding sidecar with a `(neighbors $atom $k)` grounded atom. Each is
useful alone, but the analytical lift the framework promised — neuro-symbolic
query — only materialises when the two are composed. The external analysis
named the composition pattern "embedding-veto + symbolic-veto": vector top-k
is cheap and high-recall, symbolic match is precise and expensive. Run them
in that order and the symbolic stage never has to scan the whole atomspace.

Today an author who wants "find atoms semantically similar to X that also
satisfy symbolic template P" has to write the composition by hand: call
`(neighbors ...)`, collect the result, call `(match ...)` against each
candidate. That's boilerplate that should be a single grounded atom.

## What

- Add a new `hybrid-query` capability with a `(hybrid-match $space $template $hint $k)`
  grounded atom that runs the embedding-neighbours pass first, then the
  Atomspace match second, returning the set intersection.
- Add a `(neighbors-only $space $hint $k)` grounded atom for query authors
  who want to inspect the intermediate (pre-symbolic-filter) result.
- Define a graceful fallback when the embedding sidecar is unavailable
  (pure-symbolic match over `$space` plus a surfaced warning).
- Extend `docs/booklogic-dsl-reference.md` with a "§7 Hybrid queries"
  section covering the two grounded atoms.

## Capabilities touched

- `hybrid-query` — ADD (new capability introduced by this change).

## Implementation notes

See `docs/plans/2026-05-19-tier5-metta-runtime.md`, Phase R.

## Acceptance

- `(hybrid-match $space $template $hint $k)` returns the intersection of
  the top-`$k` embedding neighbours and the symbolic-match result.
- When the embedding sidecar is unavailable, the call falls back to
  pure-symbolic match and surfaces a warning naming the sidecar.
- The "ages" fixture (10 atoms, one matching the template) returns the
  expected atom in top-1.
- `docs/booklogic-dsl-reference.md` §7 covers both grounded atoms.
