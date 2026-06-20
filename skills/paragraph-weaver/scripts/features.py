# scripts/features.py
"""Deterministic entity proxy.

v1 uses a coarse keyword extractor (content words ≥4 chars, minus a stopword and
discourse-connective list) rather than an NLP model, to stay stdlib-only and
fully reproducible. This is an entity *proxy* used for overlap-coherence and for
the bridge entity-subset guard, not a real NER. Replacing it with a pinned NER
model is a v1.5 task; the public signature must not change.
"""
from __future__ import annotations

import re

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "for",
    "from", "had", "has", "have", "in", "into", "is", "it", "its", "of", "on",
    "or", "that", "the", "their", "them", "they", "this", "to", "was", "were",
    "which", "with", "will", "would", "can", "could", "may", "might", "must",
    "not", "no", "so", "than", "then", "there", "these", "those", "such",
}

# Discourse connectives must never count as entities.
_CONNECTIVES = {
    "therefore", "however", "moreover", "thus", "hence", "because", "although",
    "whereas", "consequently", "furthermore", "nevertheless", "accordingly",
    "similarly", "conversely", "indeed", "also", "next", "finally", "first",
    "second", "third", "while", "when", "where", "here", "yet", "still",
}

_DROP = _STOPWORDS | _CONNECTIVES
_WORD = re.compile(r"[A-Za-z][A-Za-z'-]+")


def extract_entities(text: str) -> tuple[str, ...]:
    """Return a sorted tuple of distinct content-word entities (lowercased)."""
    words = (w.lower() for w in _WORD.findall(text))
    keep = {w for w in words if len(w) >= 4 and w not in _DROP}
    return tuple(sorted(keep))
