# skills/voice-eval/scripts/drift.py
"""Within-arm formula-drift monitor (REQ-VEVAL-013).

Drift = mean pairwise cosine similarity of structure vectors across an arm's passages.
Each structure vector is a bag of structural tokens: the POS sequences of the first
and last sentences (prefixed so first/last spaces are distinct) plus the opening-POS
n-gram. High mean cosine ⇒ the arm is reusing one skeleton (a formula). Analogy-family
reuse is the max count of any single base-domain family across the arm.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Callable


def _struct_terms(structure: dict) -> Counter:
    terms = Counter()
    for tok in structure.get("first", []):
        terms[f"first:{tok}"] += 1
    for tok in structure.get("last", []):
        terms[f"last:{tok}"] += 1
    terms[f"open:{'-'.join(structure.get('opening_pos', ()))}"] += 1
    return terms


def _cosine(a: Counter, b: Counter) -> float:
    keys = set(a) | set(b)
    dot = sum(a[k] * b[k] for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def arm_drift(passages: list[dict], *, struct_of: Callable[[dict], dict],
              analogy_of: Callable[[dict], str], threshold: float = 0.6) -> dict:
    vecs = [_struct_terms(struct_of(p)) for p in passages]
    pairs = [(i, j) for i in range(len(vecs)) for j in range(i + 1, len(vecs))]
    cosines = [_cosine(vecs[i], vecs[j]) for i, j in pairs]
    mean_cos = sum(cosines) / len(cosines) if cosines else 0.0
    fam_counts = Counter(analogy_of(p) for p in passages if analogy_of(p))
    reuse_max = max(fam_counts.values()) if fam_counts else 0
    return {
        "n": len(passages),
        "mean_cosine": mean_cos,
        "analogy_reuse_max": reuse_max,
        "analogy_families": dict(fam_counts),
        "threshold": threshold,
        "flagged": mean_cos > threshold,
    }


def default_struct_tokens(text: str) -> dict:
    """Real structure extractor via spaCy (used in-session, not in unit tests)."""
    import spacy
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)
    sents = list(doc.sents)
    if not sents:
        return {"first": [], "last": [], "opening_pos": ()}
    first = [t.pos_ for t in sents[0]]
    last = [t.pos_ for t in sents[-1]]
    return {"first": first, "last": last, "opening_pos": tuple(first[:3])}
