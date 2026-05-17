"""Rank candidate papers against a chapter contract using local sentence-transformer
embeddings. Deterministic, pure-function ranker. Vectors are never persisted —
only the scalar score is used downstream."""
from __future__ import annotations
from dataclasses import dataclass

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_model = None

def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(_MODEL_NAME)
        _model.eval()
    return _model

@dataclass
class Candidate:
    id: str
    title: str
    abstract: str

@dataclass
class ScoredCandidate:
    id: str
    score: float

def rank(query_text: str, candidates: list[Candidate]) -> list[ScoredCandidate]:
    if not candidates:
        return []
    import torch
    m = _get_model()
    with torch.no_grad():
        q = m.encode([query_text], convert_to_tensor=True, normalize_embeddings=True)
        d = m.encode([f"{c.title}\n\n{c.abstract}" for c in candidates],
                     convert_to_tensor=True, normalize_embeddings=True)
        sims = (d @ q.T).squeeze(1)
        scaled = (sims + 1.0) / 2.0
    pairs = [ScoredCandidate(c.id, float(s)) for c, s in zip(candidates, scaled.tolist())]
    pairs.sort(key=lambda x: -x.score)
    return pairs
