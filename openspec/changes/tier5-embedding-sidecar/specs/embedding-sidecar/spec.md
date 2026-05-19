# Capability delta: embedding-sidecar — change: tier5-embedding-sidecar

This change introduces a new capability `embedding-sidecar`,
the framework's vector index over Atomspace handles. Today no
embedding layer exists; the external analysis described this
as Layer B of the three-layer reference architecture
(symbolic Atomspace + vector sidecar + grounded computation).
After this change the framework can demonstrate symbolic ↔
subsymbolic retrieval through a `(neighbors $atom $k)` grounded
atom callable from the embedded MeTTa runtime.

## ADD

### REQ-EMBED-040 — Ubiquitous

The framework SHALL ship
`skills/neurosym-forge/scripts/_embedding_sidecar.py` providing
`class EmbeddingSidecar` with:

- `embed_atom(handle) -> np.ndarray` — embed and cache the atom
  at `handle`; return the row (L2-normalised).
- `neighbors(handle, k) -> list[tuple[Handle, float]]` — return
  top-k handles by descending cosine similarity.
- `count() -> int` — number of indexed handles.

The default encoder SHALL be
`sentence-transformers/all-MiniLM-L6-v2` (384-dim, runs locally
on CPU, no API call). The model name SHALL be overridable via
the `NEUROSYM_EMBED_MODEL` environment variable. Model loading
SHALL be lazy — the encoder is not loaded until the first
`embed_atom` call.

**Rationale:** Local-by-default keeps CI offline-capable; lazy
load keeps the sidecar's import cheap for code paths that never
call `embed_atom`.
**Tested by:** `tests/test_embedding_sidecar.py::test_top1_of_inserted_atom_is_self` (added in Q1.3)

### REQ-EMBED-041 — Ubiquitous

Each Atomspace handle SHALL get exactly one embedding row in
the sidecar's matrix; calling `embed_atom` twice on the same
handle SHALL be a no-op returning the cached row. The
sidecar's `count()` SHALL equal the number of distinct handles
indexed, NOT the number of `embed_atom` calls. REQ-EDN-065
(structural dedup at the Atomspace level) and this REQ compose:
inserting the same atom twice produces one handle, one
embedding, one row.

**Rationale:** Without this composition, the embedding budget
would be paid per insertion rather than per unique structural
shape — defeating the Atomspace's dedup property.
**Tested by:** `tests/test_embedding_sidecar.py::test_duplicate_atom_keeps_count_unchanged` (added in Q2.2)

### REQ-EMBED-042 — Optional feature

WHERE `EmbeddingSidecar.auto_embed` is True (default False), the
sidecar SHALL embed every NEW handle returned by
`Atomspace.add`. Handles returned for already-present
sub-expressions SHALL not retrigger embedding. The auto-embed
mode is opt-in because the embedding model's first load can
take several seconds and not every framework consumer wants the
sidecar active.

**Rationale:** Lets the wiki + verifier ingestion paths opt
into eager embedding; lets test paths that only exercise the
Atomspace skip the model load entirely.
**Tested by:** `tests/test_embedding_sidecar.py::test_auto_embed_indexes_every_new_atom` (added in Q3.2)

### REQ-EMBED-043 — Ubiquitous

`neighbors(handle, k)` SHALL return a list of `(handle, score)`
pairs sorted by descending cosine similarity. The returned
list SHALL satisfy:

- `len(result) <= k`,
- every `score` SHALL be in `[-1.0, 1.0]`,
- when `k > count()`, the list SHALL be of length `count()`
  (return everything, not pad with `None`),
- when the input `handle` is not indexed, the list SHALL be `[]`.

The first element SHALL be the query handle itself when the
query handle is indexed (cosine similarity with self is 1.0,
which is the maximum).

**Rationale:** Establishes the precise shape downstream callers
(the MeTTa grounded atom, the wiki retrieval surface) rely on.
**Tested by:** `tests/test_embedding_sidecar.py::test_neighbors_score_range_and_k_bounds` (added in Q4.3)

### REQ-EMBED-044 — Unwanted behaviour

IF the embedding model is unavailable (the
`sentence-transformers` package is not installed, or the model
download fails because no network is available on first load),
THEN `EmbeddingSidecar.embed_atom` SHALL raise
`EmbeddingUnavailableError` with a clear remediation message
that names the install command. The two failure paths SHALL be
distinguished in the message:

- missing package → "run: pip install 'sentence-transformers>=2.7'"
- model not cached and no network → "run:
  huggingface-cli download <model-name>"

The error SHALL be raised on first model use (lazy), NOT at
module import time, so consumers that never call `embed_atom`
do not pay for the failure.

**Rationale:** Without a clear remediation path, a CI failure
on this surface looks like "embedding broken" rather than
"action item: install one package". Naming the exact command
shortens the path from failure to fix.
**Tested by:** `tests/test_embedding_sidecar.py::test_missing_model_error_names_install_command` (added in Q5.3)

### REQ-EMBED-045 — Optional feature

WHERE the embedded MeTTa runtime is active (Phase O / change
`tier5-metta-backend`), the framework SHALL expose a grounded
atom `(neighbors $atom $k)` that wraps
`EmbeddingSidecar.neighbors`. A MeTTa program asserting
`!(neighbors (Person Alice) 5)` SHALL return five MeTTa atoms
corresponding to the five most-similar Atomspace handles.

The grounded atom SHALL be registered on each fresh `Metta`
instance at `run_metta` call time (consistent with Phase O's
per-call fresh-space pattern). When the `metta` Cargo feature
is OFF, the grounded atom SHALL NOT be registered and the
calling rule's match SHALL fail quietly (return MeTTa `()`).

**Rationale:** This is the symbolic ↔ subsymbolic seam called
out in the external analysis — the framework's MeTTa rules can
call into vector retrieval without knowing how the retrieval
is implemented.
**Tested by:** `verifiers/osmotic_pressure/rust-verifier/tests/metta_neighbors.rs::neighbors_grounded_atom_returns_five_results` (added in Q6.2)

### REQ-EMBED-046 — Ubiquitous

A new test suite at
`skills/neurosym-forge/tests/test_embedding_sidecar.py` SHALL
exercise:

- **Smoke**: insert 10 atoms, query `neighbors(h0, 5)`, assert
  top-1 = `h0` itself.
- **Dedup composition**: insert duplicate, assert `count()` is
  unchanged.
- **Missing model**: patched import raises
  `EmbeddingUnavailableError`; message contains the install
  command.
- **Score range**: every returned score is in `[-1, 1]`.
- **k bounds**: `neighbors(h, 1000)` on a 10-atom sidecar
  returns 10 results.

**Rationale:** Five test cases cover the five load-bearing
invariants the rest of the framework relies on; without all
five, a downstream regression in any of the composing
guarantees would be silent.
**Tested by:** the five test functions named above, all in `tests/test_embedding_sidecar.py` (added in Q7.1)
