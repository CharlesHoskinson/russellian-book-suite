# Capability delta: semantic-retrieval — change: tier5-semantic-retrieval

This change introduces a new capability `semantic-retrieval`,
a vector-embedding sidecar over every atom in
`work/claims.edn`. The capability is standalone Python +
numpy + sentence-transformers — no MeTTa interpreter, no
extra runtime to maintain.

## ADD

### REQ-RETRIEVAL-040 — Ubiquitous

The framework SHALL ship
`skills/neurosym-forge/scripts/_semantic_index.py` with
`class SemanticIndex` providing `embed_claim(claim_id,
text)`, `similar_claims(claim_id, k) -> list[(claim_id,
score)]`, and `count()`. The default encoder SHALL be
`sentence-transformers/all-MiniLM-L6-v2` (384-dim,
~80MB local model, no API cost); the encoder SHALL be
overridable via the `NEUROSYM_EMBED_MODEL` env var.

**Rationale:** A single Python class is the right shape for
the actual consumers (Phase R cross-chapter, Phase T
publication bridge, Phase U author CLI). The MiniLM default
gives a free, fast baseline; advanced users substitute
beefier encoders via env var without code changes.
**Tested by:** `tests/test_semantic_index_api.py::test_class_exposes_embed_similar_count` (added in Q1.1).

### REQ-RETRIEVAL-041 — Ubiquitous

`SemanticIndex` SHALL persist embeddings to
`work/semantic-index.npz` (numpy compressed archive) with
five fields: `embeddings` (N×D float32), `claim_ids` (N×
string), `model_name`, `claims_edn_sha256`, and
`schema_version`. Subsequent `make ci` runs SHALL reuse
the index without re-embedding; the cache SHALL invalidate
when the stored SHA-256 mismatches the current
`claims.edn` SHA-256 OR the stored `model_name`
mismatches the configured encoder.

**Rationale:** Embedding 1000+ claims takes seconds with
MiniLM but adds friction to every `make ci`. The SHA-256
keyed cache makes re-runs free; the model-name field
prevents silent cross-encoder drift if a user swaps
`NEUROSYM_EMBED_MODEL` without rebuilding.
**Tested by:** `tests/test_semantic_index_persistence.py::test_npz_round_trip_preserves_scores_and_cache_invalidates_on_sha_change` (added in Q2.3).

### REQ-RETRIEVAL-042 — Unwanted behaviour

IF the embedding model is unavailable (the
`sentence-transformers` package is not installed OR the
model cannot be downloaded), `embed_claim` SHALL raise
`EmbeddingUnavailableError` carrying a clear remediation
message naming the install command, the pre-fetch command,
and the `NEUROSYM_EMBED_DISABLE=1` opt-out. The rest of
the verifier path SHALL continue, treating semantic
retrieval as advisory; defects SHALL surface without a
`:semantic-neighbours` field rather than blocking the run.

**Rationale:** Semantic retrieval is a nicety, not a gate.
A network outage on first invocation must not block the
verifier from producing its verdict; the verdict simply
lacks the advisory field. The remediation message turns a
mysterious crash into a one-line fix.
**Tested by:** `tests/test_semantic_index_failure.py::test_missing_model_raises_clear_error_and_verifier_continues` (added in Q3.2).

### REQ-RETRIEVAL-043 — Optional feature

WHERE a verifier's `make ci` includes `make
index-semantic`, the framework SHALL embed every claim in
`claims.edn` during the build. Throughput SHALL be at
least ~1 second per 100 claims with the default encoder
on a single-threaded CPU.

**Rationale:** An explicit `make index-semantic` target
makes the embed step inspectable and skippable; authors who
want zero LLM cost / zero network egress simply do not
invoke it and the rest of the verifier continues.
**Tested by:** `tests/test_make_index_semantic.py::test_target_embeds_active_claims_edn` (added in Q4.1).

### REQ-RETRIEVAL-044 — Ubiquitous

The verdict surface SHALL gain a `:semantic-neighbours`
field for each defect — a vector of the top-3 most-similar
OTHER claims (excluding the defect's own claim) as
`{:claim <id> :score <float>}` entries sorted descending by
score, ties broken lexicographically by claim id for
deterministic ordering.

**Rationale:** Author-facing tooling (Phase T publication
bridge, Phase U author CLI) reads the verdict surface. By
embedding the neighbours into the verdict directly, those
tools do not need to re-load the .npz themselves —
"this defect class also potentially affects: ..." is a
zero-cost feature for downstream consumers.
**Tested by:** `tests/test_semantic_verdict.py::test_defect_has_top_3_neighbours_sorted_descending` (added in Q4.3).

### REQ-RETRIEVAL-045 — Ubiquitous

A test suite SHALL exercise the SemanticIndex contract:
inserting 10 claims followed by `similar_claims(handles[0],
3)` SHALL exclude claim 0 itself, return 3 OTHER claims
sorted descending by score with deterministic ordering, and
the persistence round-trip (save to .npz, reload from a
fresh process, query) SHALL preserve scores to 6 decimal
places.

**Rationale:** The three invariants (self-exclusion,
deterministic ordering, persistence stability) are the ones
downstream consumers rely on; testing them explicitly keeps
refactors from breaking the Phase R/T/U integrations.
**Tested by:** `tests/test_semantic_index_contract.py::test_self_excluded_ordering_deterministic_persistence_stable` (added in Q1.3 + Q2.3).

### REQ-RETRIEVAL-046 — Optional feature

WHERE the user wants to query the index from outside `make
ci` (e.g., from Phase U's author CLI), a `forge similar
<claim-id>` subcommand SHALL invoke the index and print
the top-k neighbours as tab-separated `<claim-id>\t<score>`
lines, defaulting to k=10.

**Rationale:** The author-facing CLI in Phase U needs a
stable subcommand surface; defining the contract here
keeps Phase U's wiring purely a glue task. Tab-separated
output composes with `cut`, `awk`, and the rest of the Unix
toolchain.
**Tested by:** `tests/test_forge_similar_cli.py::test_subcommand_prints_top_k_neighbours_tab_separated` (added in Q5.1).
