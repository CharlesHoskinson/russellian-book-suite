"""Stylometric primitives for Russell-Delta over MFW frequencies.

`manhattan_delta` is classic Burrows's Delta (mean absolute z-score to the author
profile) and is the discriminating single-author measure used by the scorer. The
cosine helpers are retained for pairwise stylistic comparison.
"""
from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN_RE = re.compile(r"[a-z']+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def relative_frequencies(tokens: list[str], mfw: list[str]) -> list[float]:
    total = len(tokens)
    if total == 0:
        return [0.0] * len(mfw)
    counts = Counter(tokens)
    return [counts.get(w, 0) / total for w in mfw]


def zscore(freqs: list[float], mean: list[float], stdev: list[float]) -> list[float]:
    return [(f - m) / s if s > 0 else 0.0 for f, m, s in zip(freqs, mean, stdev)]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def cosine_delta(a: list[float], b: list[float]) -> float:
    return 1.0 - cosine(a, b)


def manhattan_delta(z: list[float]) -> float:
    """Classic Burrows's Delta: mean absolute z-score (distance to the author profile)."""
    return sum(abs(x) for x in z) / len(z) if z else 0.0
