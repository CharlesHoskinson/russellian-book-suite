# Design: tier5-embedding-sidecar

## Choice of default encoder

Three candidates were considered:

- **(a) `sentence-transformers/all-MiniLM-L6-v2`.** 384-dim, ~80
  MB on disk, runs locally on CPU in ~10 ms per atom. No API key,
  no network during CI once the model is cached in
  `~/.cache/huggingface/`.
- (b) OpenAI `text-embedding-3-small`. 1536-dim, network-bound,
  costs per call, requires `OPENAI_API_KEY`. Bans the framework
  from offline CI.
- (c) Hand-rolled hash embedding (e.g. SimHash over the atom's
  canonical written form). Free, deterministic, but tells you
  nothing about semantic similarity — defeats Layer B's purpose.

**Decision: (a).** Local, free, semantically-meaningful, and
the same model the russellian-book-suite already pulls in for
the `wiki-*` skills (avoids adding a second sentence-transformer
to the install footprint). The choice is overridable via
`NEUROSYM_EMBED_MODEL`, so a user with an existing OpenAI
account can swap to text-embedding-3-small with a one-line env
change.

## Module shape

```python
import numpy as np

class EmbeddingSidecar:
    """Vector index over Atomspace handles. Lazy model load."""

    DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self, atomspace, *, auto_embed: bool = False,
                 model_name: str | None = None):
        self.atomspace = atomspace
        self.auto_embed = auto_embed
        self._model_name = model_name or os.environ.get(
            "NEUROSYM_EMBED_MODEL", self.DEFAULT_MODEL)
        self._model = None              # lazy
        self._matrix: np.ndarray | None = None  # (N, dim)
        self._handle_to_row: dict[Handle, int] = {}

    def _ensure_model(self) -> None:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as e:
                raise EmbeddingUnavailableError(
                    f"sentence-transformers not installed; "
                    f"run: pip install 'sentence-transformers>=2.7'"
                ) from e
            try:
                self._model = SentenceTransformer(self._model_name)
            except OSError as e:
                raise EmbeddingUnavailableError(
                    f"embedding model {self._model_name!r} unavailable "
                    f"(no network on first load?); "
                    f"run: huggingface-cli download {self._model_name}"
                ) from e

    def embed_atom(self, handle: Handle) -> np.ndarray: ...
    def neighbors(self, handle: Handle, k: int) -> list[tuple[Handle, float]]: ...
    def count(self) -> int: ...
```

## Composition with REQ-EDN-065 dedup

The Atomspace's `add` is idempotent on structurally identical
input. The sidecar's `embed_atom` is idempotent on identical
handle: if `_handle_to_row` already contains the handle, return
the cached row without re-running the encoder. The two
idempotencies compose: inserting the same atom twice produces
one handle, one embedding, one row in the matrix.

The auto-embed mode (off by default; opt-in via
`EmbeddingSidecar.auto_embed = True`) wires this composition
the other direction: the sidecar registers itself as a listener
on `Atomspace.add`. When a NEW handle is created, the sidecar
embeds it; when an existing handle is returned, nothing happens.

## Nearest-neighbour query

`neighbors(handle, k)` returns a list of `(handle, score)` pairs
sorted by descending cosine similarity. Implementation:

```python
def neighbors(self, handle, k):
    self._ensure_model()
    if self._matrix is None or handle not in self._handle_to_row:
        return []
    row_idx = self._handle_to_row[handle]
    query = self._matrix[row_idx]
    # cosine: rows are L2-normalised at insert time
    scores = self._matrix @ query
    # top-k including self
    top_idx = np.argsort(-scores)[:k]
    row_to_handle = {v: k for k, v in self._handle_to_row.items()}
    return [(row_to_handle[i], float(scores[i])) for i in top_idx]
```

Scores are in `[-1, 1]` because rows are L2-normalised at insert
time. `k` is upper-bounded by `count()`; queries with `k >
count()` simply return everything.

## Persistence

No persistence in this tier. Each fresh verifier process rebuilds
the matrix from scratch (cheap: 384 dims * a few thousand atoms *
4 bytes ≈ a few MB; building the matrix from scratch on every
`make ci` is < 30 s on the largest fixture).

A future tier wires this to FAISS (in-process IVF index) or
pgvector (out-of-process Postgres extension) — out of scope here.

## Grounded-atom wiring into MeTTa

hyperon-experimental's grounded-atom protocol allows native Rust
functions to participate in MeTTa evaluation. The framework
exposes `(neighbors $atom $k)` as a grounded atom registered on
each fresh `Metta` instance at `run_metta` call time:

```rust
// Sketch — exact API depends on the pinned hyperon rev
let neighbors_grounded = GroundedAtom::new("neighbors", |args| {
    let atom = args[0];
    let k = args[1].as_int()?;
    let py = python::call("embedding_sidecar.neighbors_grounded",
                          &[atom, k])?;
    Ok(py.into())
});
metta.register_grounded("neighbors", neighbors_grounded);
```

The Python side exposes `neighbors_grounded(atom_repr, k)` via a
small CFFI shim; the Rust side calls into Python only when the
`metta` Cargo feature AND the embedding sidecar are both
available. Without those, `(neighbors $atom $k)` evaluates to
`()` (the MeTTa empty atom) and the calling rule's match fails
quietly.

This is the symbolic ↔ subsymbolic seam the external analysis
called out: MeTTa rules can call into vector retrieval without
knowing how the retrieval is implemented.

## Failure modes

| Cause                                  | Behaviour                                       |
|----------------------------------------|-------------------------------------------------|
| `sentence-transformers` not installed  | `EmbeddingUnavailableError` with `pip install` hint |
| Model name unknown / no network        | `EmbeddingUnavailableError` with `huggingface-cli` hint |
| `embed_atom` called twice on same handle | No-op; returns cached row                     |
| `neighbors(handle, k)` with `k > count()` | Returns everything, length `count()`         |
| `neighbors(unknown_handle, k)`         | Returns `[]`                                    |
| `metta` feature off, grounded atom called | Returns MeTTa `()`; rule match fails         |

## Test surface

A new test file
`skills/neurosym-forge/tests/test_embedding_sidecar.py`
exercises:

- **Smoke** — insert 10 atoms, query `neighbors(h0, 5)`, assert
  top-1 = `h0` itself (the matrix contains the query row, so
  self-similarity is 1.0).
- **Dedup composition** — insert duplicate, assert
  `EmbeddingSidecar.count()` is unchanged.
- **Missing model** — patch the import to raise, assert
  `EmbeddingUnavailableError` is raised with the install command
  in its message.
- **Score range** — every score returned is in `[-1, 1]`.
- **k > N** — `neighbors(h, 1000)` on a 10-atom sidecar returns
  10 results, not 1000.

A separate Rust-side test
`verifiers/osmotic_pressure/rust-verifier/tests/metta_neighbors.rs`
runs a MeTTa program with `!(neighbors (Person Alice) 5)` and
asserts five results are returned (only when the `metta` feature
is on; gated on `cfg(feature = "metta")`).
