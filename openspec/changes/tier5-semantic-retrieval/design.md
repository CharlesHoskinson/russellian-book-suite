# Design: tier5-semantic-retrieval

## Encoder choice

`sentence-transformers/all-MiniLM-L6-v2` chosen on three
axes:

1. **Local model, no API cost.** Embedding model weights
   ship via the `sentence-transformers` Hugging Face cache
   (~80MB, one-time download). After the first run every
   embed is free; CI does not bill per claim.
2. **384-dim is the right magnitude.** Cosine similarity
   over 384-dim vectors is fast (microseconds per pair) and
   the disk footprint at 1000 claims is ~1.5MB — fits in the
   `work/` directory without ceremony.
3. **Widely-used baseline.** MTEB-leaderboard reference; if
   the framework ever wants to compare alternatives, this is
   the apples-to-apples baseline. Authors who want a beefier
   encoder set `NEUROSYM_EMBED_MODEL=sentence-transformers/all-mpnet-base-v2`
   or similar — the interface is encoder-agnostic.

Alternative considered: OpenAI `text-embedding-3-small` (1536
dim). Rejected because (a) API-cost per claim, (b) the
extra dimensionality buys nothing at this corpus scale,
(c) requires `OPENAI_API_KEY` in CI.

## Persistence shape

`work/semantic-index.npz` written via `np.savez_compressed`:

```python
np.savez_compressed(
    "work/semantic-index.npz",
    embeddings=embeddings,        # (N, 384) float32
    claim_ids=claim_ids,          # (N,) U64 string
    model_name=np.array([model_name], dtype="U128"),
    claims_edn_sha256=np.array([sha256], dtype="U64"),
    schema_version=np.array([1], dtype="i4"),
)
```

The five fields together let the loader:

- decide whether to re-embed (if `claims_edn_sha256`
  changed),
- detect cross-encoder drift (refuse to load if
  `model_name` mismatches the configured encoder),
- migrate forward on `schema_version` bumps.

Load path: `np.load("work/semantic-index.npz")` then
mmap-friendly slicing for `similar_claims` queries.

## Cache-invalidation discipline

`claims.edn`'s SHA-256 is stored in the .npz. On every
`SemanticIndex.__init__`:

1. Compute the current `claims.edn` SHA-256.
2. If the .npz file exists AND its stored SHA-256 matches
   the current one AND its stored `model_name` matches the
   configured encoder, mmap the existing embeddings.
3. Otherwise mark as stale and require `embed_claim` to be
   driven afresh (typically via `make index-semantic`).

Authors who run `make ci` repeatedly with no claim changes
see the index re-used. Authors who add a claim see the
index re-built. Authors who switch encoders see a fresh
build.

## API surface

```python
class SemanticIndex:
    def __init__(
        self,
        npz_path: Path = Path("work/semantic-index.npz"),
        claims_edn_path: Path = Path("work/claims.edn"),
        model_name: str | None = None,  # defaults to env var
    ) -> None: ...

    def embed_claim(
        self,
        claim_id: str,
        text: str,
    ) -> None: ...

    def similar_claims(
        self,
        claim_id: str,
        k: int = 3,
    ) -> list[tuple[str, float]]: ...

    def count(self) -> int: ...

    def save(self) -> None: ...
```

`similar_claims` returns `(other_claim_id, cosine_score)`
sorted descending by score; ties broken lexicographically by
`other_claim_id` for deterministic ordering. The querying
claim itself is excluded from the result.

## :semantic-neighbours verdict field

For every defect surfaced by the verifier, the verdict gains:

```edn
{:defects
  [{:claim "C014"
    :reason :inequality-violation
    :semantic-neighbours
      [{:claim "C247" :score 0.91}
       {:claim "C082" :score 0.88}
       {:claim "C031" :score 0.86}]}]}
```

Top-3 most-similar OTHER claims. Author-facing tooling
(Phase T) can render "this defect class also potentially
affects: ..." without having to recompute embeddings.

## Failure path: missing model

`EmbeddingUnavailableError` is raised when
`sentence-transformers` is not installed OR when the model
download fails (no network on first invocation):

```python
class EmbeddingUnavailableError(RuntimeError):
    """The semantic index could not load its encoder.

    Remediation:
      - install sentence-transformers: `pip install
        sentence-transformers`
      - or pre-fetch the model: `python -c "from
        sentence_transformers import SentenceTransformer;
        SentenceTransformer('{model}')"`
      - or set NEUROSYM_EMBED_DISABLE=1 to run the verifier
        without semantic retrieval (defects will have no
        :semantic-neighbours field).
    """
```

The verifier path SHALL continue when this error fires;
semantic retrieval is advisory, not gating.

## CLI entry

`forge similar <claim-id>` invokes:

```python
idx = SemanticIndex()
for cid, score in idx.similar_claims(claim_id, k=10):
    print(f"{cid}\t{score:.3f}")
```

Output is tab-separated for shell composition. Phase U's
author CLI wires this as a subcommand.

## Why NOT bundle into a MeTTa grounded atom this time

The previous Tier 5 plan exposed semantic retrieval as a
MeTTa grounded atom `(similar! claim_id k)`. That surface
required:

- a MeTTa interpreter running at make-ci time,
- a grounded-atom registration path,
- a marshalling layer between MeTTa atoms and the
  numpy-shaped index.

For the actual use cases — Phase R cross-chapter
consistency, Phase T publication bridge, Phase U author CLI
— none of those consumers want a MeTTa surface. They want a
Python function. The standalone sidecar is the right shape;
the MeTTa grounded atom was over-engineering.

If a MeTTa runtime is ever shipped (it is not on the
roadmap), this sidecar is trivially wrappable in a grounded
atom — the dependency arrow points the right way.

## Why not bundle into Phase O (scale-corpus) or Phase P (LLM lifts)?

Phase O exercises Phase Q's index at scale — that is the
right consumer. But authoring the index alongside Phase O
would conflate "build the scale verifier" with "design the
embedding API", and the embedding API has its own
correctness shape (encoder choice, persistence, cache
invalidation) that deserves its own change folder. Phase Q
ships the API; Phase O exercises it as one of many
consumers.

Phase P (LLM lifts) shares zero infrastructure with Phase Q.
The LLM is a JSON-producing oracle; the embedding is a
vector-producing function. Different failure modes,
different caches, different security models.
