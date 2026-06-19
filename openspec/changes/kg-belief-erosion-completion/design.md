# Design: kg-belief-erosion-completion

## Storage and Relation

S5 adds one graph relation, `effective-confidence`, to `skills/book-knowledge/assets/kg-schema.edn`.
It is a derived Cozo relation, not a ledger record. Each materialization run writes
one row per latest-per-id claim into the supplied Cozo store:

- `id` / `claim-id`: the claim id. The row upserts by claim id for the requested snapshot.
- `prior`: the claim prior used by the belief engine.
- `posterior`: the posterior returned by `propagate_belief.propagate`.
- `effective`: the query-facing confidence value. In S5 it is the engine posterior
  under decayed source trust and trusted-conflict dampers.
- `freshness-factor`: the minimum source freshness factor applied to the claim's sources.
- `support-erosion-reason-json`: canonical JSON for the minimal erosion reason.
- `as-of`: the explicit snapshot reference timestamp.

The materializer leaves `claims/ledger.jsonl` byte-identical. It may load the
derived relation in an in-memory or caller-owned Cozo store.

## Deterministic Freshness

Freshness decay never uses the system clock. The reference time is an explicit
`as_of` argument to the effective-confidence path. `belief_graph.load_source_trust`
keeps its previous behavior when `as_of` is omitted; when supplied, it multiplies
manifest trust by:

`0.5 ** (age_days / half_life_days)`

The default half-life is 365 days. Future timestamps clamp to age zero. Invalid or
missing manifest timestamps are ignored by callers that do not request freshness.

## Engine Reuse

The materializer calls `propagate_belief.propagate` directly. It does not rewrite
the evidence combine, counter-claim damping, derivation attenuation, or iterative
convergence rules. The only new inputs are deterministic:

- source trust already loaded from manifests, optionally age-decayed by explicit
  reference time;
- latest-per-id counter-claims from `claims/counter-claims.jsonl`;
- synthetic open counter-claim inputs for fresh trusted `conflicts_with` edges.

The synthetic conflict inputs reuse the engine's existing open-counter-claim damping.
A conflict is eligible when a current claim declares `conflicts_with` against the
target, the conflicting claim has a source manifest whose `ingested_at` is later
than the target claim's `created_at`, and the decayed source trust is at least 0.5.

## Erosion Reason

A claim whose effective confidence is below its prior receives a canonical,
bounded reason list. Reasons are selected under fixed ordering:

1. Current non-dismissed counter-claims targeting the claim.
2. The weakest direct parent whose own posterior is below its prior.
3. Fresh trusted conflict sources converted to synthetic engine dampers.
4. Stale source decay when a source freshness factor falls below 0.95.

For the propagation math currently in the engine, all non-dismissed counter-claims
are multiplicative dampers and the derivation rule uses the weakest parent only.
The reason list therefore names the minimal responsible facts exposed by those
two damping modes. Fresh conflict reasons name the refreshed source and the
conflict claim that introduced the trusted attack.

## Why-Provenance

Why-provenance is on demand. `compute_why_provenance` accepts flagged claim ids and
returns rows only for flagged load-bearing claims. Non-flagged claims and flagged
non-load-bearing claims are skipped.

The witness set is direct and bounded: parent claim ids first, then source ids,
both in canonical order. If the direct witness set exceeds the supplied bound, the
returned row contains only the bounded prefix and `truncated: true`. The function
does not recurse unboundedly.

The cache is append-only under `claims/why-provenance.jsonl`. This resolves the
read-only materialization contract: `effective-confidence` never writes the ledger,
while optional why-provenance caching writes a separate sidecar and never mutates
an existing ledger record.

## Determinism

All result sets are canonical-sortable and contain no wall-clock values. The caller
supplies `as_of`; the materializer canonicalizes it to UTC `Z` form. Re-running on
the same ledger, manifests, counter-claims, and `as_of` produces result-set-equal
rows.
