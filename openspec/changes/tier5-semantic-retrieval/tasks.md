# Tasks: tier5-semantic-retrieval

See `docs/plans/2026-05-19-tier5-scale-author.md` Phase Q for full
TDD steps. Task numbers correspond 1:1.

## Phase Q.1 — SemanticIndex class + encoder integration

- [ ] Q1.1: Author `skills/neurosym-forge/scripts/_semantic_index.py` with `class SemanticIndex` exposing `embed_claim`, `similar_claims`, `count`, `save`. (REQ-RETRIEVAL-040)
- [ ] Q1.2: Wire `sentence-transformers/all-MiniLM-L6-v2` as the default encoder; override via `NEUROSYM_EMBED_MODEL`. (REQ-RETRIEVAL-040)
- [ ] Q1.3: Test 10-claim insertion: `similar_claims(handles[0], 3)` returns claim 0 itself excluded and three other claims sorted descending by score, deterministic ordering. (REQ-RETRIEVAL-045)

## Phase Q.2 — Persistence + cache invalidation

- [ ] Q2.1: `save()` writes `work/semantic-index.npz` via `np.savez_compressed` with fields `embeddings`, `claim_ids`, `model_name`, `claims_edn_sha256`, `schema_version`. (REQ-RETRIEVAL-041)
- [ ] Q2.2: `__init__` checks the stored SHA-256 against the current `claims.edn` SHA-256; mismatch marks the index stale and forces re-embed. Encoder name mismatch refuses to load with a clear error. (REQ-RETRIEVAL-041)
- [ ] Q2.3: Persistence round-trip test: write 10 claims, reload, scores between any two surviving claims unchanged to 6 decimal places. (REQ-RETRIEVAL-045)

## Phase Q.3 — Failure path + advisory continuation

- [ ] Q3.1: `embed_claim` raises `EmbeddingUnavailableError` when `sentence-transformers` is missing or the model download fails; the error message names the three remediations. (REQ-RETRIEVAL-042)
- [ ] Q3.2: Verifier path catches `EmbeddingUnavailableError`, logs a warning, and continues without `:semantic-neighbours` populated. (REQ-RETRIEVAL-042)

## Phase Q.4 — make index-semantic + verdict surface

- [ ] Q4.1: Add `make index-semantic` target to the project-template Makefile invoking `python -m scripts.index_semantic`. (REQ-RETRIEVAL-043)
- [ ] Q4.2: The verifier path computes `:semantic-neighbours` for every defect — top-3 most-similar OTHER claims. (REQ-RETRIEVAL-044)
- [ ] Q4.3: Test verdict-surface integration: a doctored fixture surfaces a defect with `:semantic-neighbours` populated and ordered by descending score. (REQ-RETRIEVAL-044)

## Phase Q.5 — forge similar CLI + commit

- [ ] Q5.1: Add `forge similar <claim-id>` subcommand printing tab-separated `<claim-id>\t<score>` lines for the top-k neighbours. (REQ-RETRIEVAL-046)
- [ ] Q5.2: Document in `docs/booklogic-dsl-reference.md` — new §8 Semantic Retrieval naming the encoder, the persistence shape, and the `:semantic-neighbours` field.
- [ ] Q5.3: Commit once Q1-Q5 are green.
