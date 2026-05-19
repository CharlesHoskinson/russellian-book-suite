# Tasks: tier5-embedding-sidecar

See `docs/plans/2026-05-19-tier5-metta-runtime.md` Phase Q for
full TDD steps. Task numbers correspond 1:1.

## Phase Q.1 — Sidecar module

- [ ] Q1.1: Create `skills/neurosym-forge/scripts/_embedding_sidecar.py` exposing `class EmbeddingSidecar` with `embed_atom`, `neighbors`, `count`, and `EmbeddingUnavailableError`. (REQ-EMBED-040)
- [ ] Q1.2: Wire the default encoder `sentence-transformers/all-MiniLM-L6-v2` with lazy model load and `NEUROSYM_EMBED_MODEL` env override. (REQ-EMBED-040)
- [ ] Q1.3: Failing smoke test `tests/test_embedding_sidecar.py::test_top1_of_inserted_atom_is_self` over a 10-atom fixture. Commit.

## Phase Q.2 — Dedup composition

- [ ] Q2.1: `embed_atom(handle)` SHALL be idempotent on the handle: re-call is a no-op returning the cached row. (REQ-EMBED-041)
- [ ] Q2.2: Failing test `tests/test_embedding_sidecar.py::test_duplicate_atom_keeps_count_unchanged` asserts REQ-EDN-065 + REQ-EMBED-041 compose. Commit.

## Phase Q.3 — Auto-embed mode

- [ ] Q3.1: Add `auto_embed: bool = False` constructor flag; when True, the sidecar embeds every NEW handle returned by `Atomspace.add`. (REQ-EMBED-042)
- [ ] Q3.2: Failing test `tests/test_embedding_sidecar.py::test_auto_embed_indexes_every_new_atom` covers the mode. Commit.

## Phase Q.4 — neighbors query

- [ ] Q4.1: Implement `neighbors(handle, k) -> list[tuple[Handle, float]]`; rows are L2-normalised at insert time so the dot product is cosine similarity. (REQ-EMBED-043)
- [ ] Q4.2: Score range and `k > count()` bounds checks. (REQ-EMBED-043)
- [ ] Q4.3: Failing test `tests/test_embedding_sidecar.py::test_neighbors_score_range_and_k_bounds`. Commit.

## Phase Q.5 — Failure paths

- [ ] Q5.1: `EmbeddingUnavailableError` raised on missing `sentence-transformers` import with `pip install` hint. (REQ-EMBED-044)
- [ ] Q5.2: `EmbeddingUnavailableError` raised on model-load OSError with `huggingface-cli download` hint. (REQ-EMBED-044)
- [ ] Q5.3: Failing test `tests/test_embedding_sidecar.py::test_missing_model_error_names_install_command`. Commit.

## Phase Q.6 — MeTTa grounded atom

- [ ] Q6.1: Add `verifiers/*/rust-verifier/src/metta_grounded.rs` registering `(neighbors $atom $k)` against each fresh `Metta` instance, gated on `cfg(feature = "metta")`. (REQ-EMBED-045)
- [ ] Q6.2: Failing Rust test `tests/metta_neighbors.rs::neighbors_grounded_atom_returns_five_results` runs a MeTTa program asserting `!(neighbors (Person Alice) 5)`. Commit.
- [ ] Q6.3: Test suite asserts the grounded atom evaluates to `()` when `metta` feature is off. Commit.

## Phase Q.7 — Integration test + open PR

- [ ] Q7.1: Add `tests/test_embedding_sidecar.py` covering all five test cases from `design.md`'s test-surface section. (REQ-EMBED-046)
- [ ] Q7.2: Push branch `plan/tier5-metta-runtime`; open PR; merge on green CI.
