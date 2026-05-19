# Change: tier5-embedding-sidecar

**Tier:** 5 of 5 (vector sidecar for symbolic atoms)
**Branch:** `plan/tier5-metta-runtime`
**Depends on:** Tier 5 (metta-backend, edn-metta-bijection)

## Why

The external analysis comparing neurosym-forge to MeTTa /
Atomspace described a three-layer reference architecture:

- **Layer A: symbolic Atomspace.** Provided in this tier by
  `tier5-edn-metta-bijection` (`_atomspace.py`).
- **Layer B: vector sidecar.** Every atom in the Atomspace is
  indexed with an embedding; nearest-neighbour retrieval is
  available through a `(neighbors $atom $k)` grounded atom that
  the MeTTa runtime can call.
- **Layer C: grounded computation.** Provided in this tier by
  `tier5-metta-backend` (hyperon-experimental's grounded-atom
  protocol).

Today's neurosym-forge ships Layer C (in this tier) and Layer A
(in this tier), but no Layer B. Without it, the framework
cannot demonstrate symbolic ↔ subsymbolic retrieval — the
single most-cited reason MeTTa-shaped infrastructure exists
above pure Datalog.

## What

- Ship `skills/neurosym-forge/scripts/_embedding_sidecar.py`
  exposing `class EmbeddingSidecar` with `embed_atom(handle)`,
  `neighbors(handle, k)`, and `count()`.
- Default encoder: `sentence-transformers/all-MiniLM-L6-v2`
  (384-dim, local, no API call); overridable via
  `NEUROSYM_EMBED_MODEL` env var.
- Each Atomspace handle gets exactly one embedding; re-insertion
  is a no-op (REQ-EDN-065's dedup composes with this).
- A grounded atom `(neighbors $atom $k)` wires the sidecar into
  the embedded MeTTa runtime via hyperon-experimental's grounded
  atom protocol.
- In-memory NumPy storage; no persistent vector DB in this tier
  (FAISS / pgvector deferred to a future tier).
- Missing-model failure path raises `EmbeddingUnavailableError`
  with a clear install command.

## Capabilities touched

- `embedding-sidecar` — ADD (new capability; vector index over
  the Atomspace)

## Implementation notes

See `docs/plans/2026-05-19-tier5-metta-runtime.md`, Phase Q.

## Acceptance

- 7 REQ-EMBED-040..046 IDs ship in
  `specs/embedding-sidecar/spec.md`.
- A smoke test inserts 10 atoms, queries top-5 neighbours of
  one, asserts top-1 = self.
- A dedup-composition test inserts the same atom twice and
  asserts `EmbeddingSidecar.count()` is unchanged.
- A missing-model test triggers `EmbeddingUnavailableError`
  with a remediation message naming the install command.
- A MeTTa program asserting `(neighbors (Person Alice) 5)`
  returns the five most-similar atoms when the metta feature
  is enabled.
