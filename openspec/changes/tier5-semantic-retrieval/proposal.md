# Change: tier5-semantic-retrieval

**Tier:** 5 of 5 (scale + author-facing tier)
**Branch:** `plan/tier5-scale-author`
**Depends on:** Tier 1 (binding-schema)

## Why

The framework today has no semantic surface over its claim
set. Every claim relationship the verifier reasons over must
be encoded structurally: same predicate, same subject,
matching args. "Find claims about this concept" — the
question every author asks after their fifth chapter —
falls out of scope. Cross-paragraph consistency (Phase R)
needs a way to ask "which other claims are about this same
trial without the trial ID being explicit"; author-facing
tooling (Phase T's publication bridge, Phase U's author CLI)
needs a way to ask "have I cited something like this
before".

The previous Tier 5 plan bundled this with a MeTTa-runtime
grounded atom — an interpreter-shaped surface for what is
actually a one-function library. That plan was rejected as
over-engineered. This change ships the same semantic-search
capability as a standalone Python sidecar: numpy +
sentence-transformers, no MeTTa, no interpreter dependency,
no extra runtime to maintain.

## What

- A `SemanticIndex` class at
  `skills/neurosym-forge/scripts/_semantic_index.py` with
  `embed_claim(claim_id, text)`,
  `similar_claims(claim_id, k) -> list[(claim_id, score)]`,
  and `count()`.
- Default encoder: `sentence-transformers/all-MiniLM-L6-v2`
  (384-dim, ~80MB model, no API cost); overridable via
  `NEUROSYM_EMBED_MODEL`.
- Persistence to `work/semantic-index.npz` via
  `np.savez_compressed`; cache invalidates on
  `claims.edn` SHA-256 checksum change.
- A `make index-semantic` target embedding every claim in
  the active `claims.edn`.
- A `:semantic-neighbours` field on the verdict surface —
  for each defect, the top-3 most-similar OTHER claims, so
  author-facing tooling can show "this defect class also
  potentially affects: ...".
- A `forge similar <claim-id>` CLI entry for external
  queries (Phase U's author CLI will wire this).

## Capabilities touched

- `semantic-retrieval` — ADD (new capability; vector-index
  sidecar over the claim set, distinct from the structural
  Datalog surface in Tier 3)

## Implementation notes

See `docs/plans/2026-05-19-tier5-scale-author.md`, Phase Q.

## Acceptance

- 7 REQ-RETRIEVAL IDs ship in
  `specs/semantic-retrieval/spec.md`.
- `make index-semantic` embeds the active `claims.edn`;
  `forge similar <claim-id>` prints the top-k neighbours.
- The verdict surface gains `:semantic-neighbours` for
  every defect.
- Persistence round-trip preserves embeddings byte-stable.
- The first-download failure path raises
  `EmbeddingUnavailableError` with a clear remediation
  message; the rest of the verifier continues.
