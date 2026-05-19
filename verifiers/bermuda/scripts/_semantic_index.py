"""REQ-RETRIEVAL-040..046: vector embedding sidecar.

Default encoder: sentence-transformers/all-MiniLM-L6-v2 (384-dim).
Persists to a single .npz keyed by claims.edn SHA-256 (cache-invalidates
on claim-set change).

Standalone Python sidecar — no MeTTa runtime dependency. The model is
loaded lazily so `pytest.importorskip("sentence_transformers")`-gated
tests skip cleanly when the optional dependency is absent.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Optional

import numpy as np


class EmbeddingUnavailableError(RuntimeError):
    """Embedding model unavailable.

    Raised when ``sentence_transformers`` is not installed OR the model
    download fails (no network on first invocation). The verifier path
    SHALL continue when this error fires; semantic retrieval is
    advisory, not gating.

    Remediation:
      - install sentence-transformers: ``pip install sentence-transformers``
      - or pre-fetch the model: ``python -c "from sentence_transformers
        import SentenceTransformer; SentenceTransformer('<model>')"``
      - or set ``NEUROSYM_EMBED_DISABLE=1`` to run the verifier without
        semantic retrieval (defects will have no ``:semantic-neighbours``
        field).
    """


_DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
# all-MiniLM-L6-v2 emits 384-dim vectors. Kept as a constant so the
# empty-save path produces a shape-consistent .npz.
_DEFAULT_DIM = 384


class SemanticIndex:
    """Vector index over a claim set.

    Embeds each claim's :doc text with a sentence-transformers encoder,
    persists the (N, D) float32 matrix plus the claim_ids vector to a
    single .npz, and answers ``similar_claims(claim_id, k)`` via cosine
    similarity (dot product over normalised vectors).
    """

    def __init__(
        self,
        *,
        cache_path: Optional[Path] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self._cache_path = Path(cache_path) if cache_path else None
        self._model_name = model_name or os.environ.get(
            "NEUROSYM_EMBED_MODEL", _DEFAULT_MODEL
        )
        self._model = None
        self._claim_ids: list[str] = []
        self._embeddings: list[np.ndarray] = []
        self._claims_sha: str = ""

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _ensure_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as e:  # pragma: no cover - exercised via test
                raise EmbeddingUnavailableError(
                    "sentence-transformers not installed; "
                    "remediation: `pip install sentence-transformers` "
                    "(or set NEUROSYM_EMBED_DISABLE=1 to skip semantic "
                    "retrieval; defects will have no :semantic-neighbours "
                    "field)."
                ) from e
            try:
                self._model = SentenceTransformer(self._model_name)
            except Exception as e:  # network / cache failure
                raise EmbeddingUnavailableError(
                    f"failed to load encoder {self._model_name!r}; "
                    f"remediation: pre-fetch with `python -c \"from "
                    f"sentence_transformers import SentenceTransformer; "
                    f"SentenceTransformer('{self._model_name}')\"` "
                    f"or `pip install sentence-transformers` then retry; "
                    f"underlying error: {e}"
                ) from e
        return self._model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def embed_claim(self, *, claim_id: str, text: str) -> None:
        """Embed a single claim. Idempotent on repeat ``claim_id``."""
        if claim_id in self._claim_ids:
            return
        vec = self._ensure_model().encode(
            [text], normalize_embeddings=True
        )[0]
        self._claim_ids.append(claim_id)
        self._embeddings.append(np.asarray(vec, dtype=np.float32))

    def similar_claims(
        self, claim_id: str, k: int = 5
    ) -> list[tuple[str, float]]:
        """Return up to k (other_claim_id, cosine_score) tuples sorted
        descending by score. Ties broken lexicographically by claim_id
        for deterministic ordering. The querying claim itself is
        included as the first entry (score ~= 1.0); callers that want
        OTHER claims only should slice from index 1 or use
        ``similar_other_claims``.
        """
        if claim_id not in self._claim_ids:
            raise KeyError(f"claim_id {claim_id!r} not in index")
        i = self._claim_ids.index(claim_id)
        query = self._embeddings[i]
        scored = [
            (cid, float(np.dot(query, emb)))
            for cid, emb in zip(self._claim_ids, self._embeddings)
        ]
        # Sort: descending score, then ascending claim_id for ties.
        scored.sort(key=lambda kv: (-kv[1], kv[0]))
        return scored[:k]

    def similar_other_claims(
        self, claim_id: str, k: int = 3
    ) -> list[tuple[str, float]]:
        """``similar_claims`` with the querying claim itself excluded.

        This is the shape the verdict ``:semantic-neighbours`` field
        consumes (REQ-RETRIEVAL-044).
        """
        if claim_id not in self._claim_ids:
            raise KeyError(f"claim_id {claim_id!r} not in index")
        # Pull k+1 so we can drop self and still return up to k entries.
        all_neighbours = self.similar_claims(claim_id, k=k + 1)
        return [(cid, score) for cid, score in all_neighbours if cid != claim_id][:k]

    def count(self) -> int:
        return len(self._claim_ids)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def claims_sha(self) -> str:
        return self._claims_sha

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Persist to ``self._cache_path`` as ``np.savez_compressed``.

        Five fields per REQ-RETRIEVAL-041:
          - embeddings (N, D) float32
          - claim_ids (N,) unicode
          - model_name (1,) unicode
          - claims_sha (1,) unicode (claims.edn SHA-256)
          - schema_version (1,) int32
        """
        if not self._cache_path:
            return
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        if self._embeddings:
            embeddings = np.vstack(self._embeddings).astype(np.float32)
        else:
            embeddings = np.zeros((0, _DEFAULT_DIM), dtype=np.float32)
        np.savez_compressed(
            self._cache_path,
            embeddings=embeddings,
            claim_ids=np.asarray(self._claim_ids, dtype=object),
            model_name=np.asarray([self._model_name], dtype=object),
            claims_sha=np.asarray([self._claims_sha], dtype=object),
            schema_version=np.asarray([1], dtype=np.int32),
        )

    def load(self) -> None:
        """Load embeddings from ``self._cache_path`` if it exists.

        Refuses to load if the stored ``model_name`` mismatches the
        configured encoder (per REQ-RETRIEVAL-041 cross-encoder drift
        guard). On mismatch the in-memory state is left empty so the
        caller can rebuild.
        """
        if not self._cache_path or not self._cache_path.exists():
            return
        z = np.load(self._cache_path, allow_pickle=True)
        stored_model = (
            str(z["model_name"][0]) if "model_name" in z.files else ""
        )
        if stored_model and stored_model != self._model_name:
            # Cross-encoder drift: refuse to load, leave state empty.
            return
        embeddings = z["embeddings"]
        self._claim_ids = [str(cid) for cid in z["claim_ids"]]
        self._embeddings = [
            np.asarray(embeddings[i], dtype=np.float32)
            for i in range(embeddings.shape[0])
        ]
        self._claims_sha = (
            str(z["claims_sha"][0]) if "claims_sha" in z.files else ""
        )

    def invalidate_if_claims_changed(self, claims_text: str) -> None:
        """Drop the in-memory embeddings if the current claims.edn
        SHA-256 differs from the stored one. Updates the stored SHA in
        either case so the next ``save()`` records the current claim
        set.
        """
        current_sha = hashlib.sha256(
            claims_text.encode("utf-8")
        ).hexdigest()
        if self._claims_sha and self._claims_sha != current_sha:
            self._claim_ids = []
            self._embeddings = []
        self._claims_sha = current_sha
