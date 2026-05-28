"""Order-sensitive liveness signals (stdlib only; no spaCy, no lint_common).

nPVI (normalized pairwise variability index; Grabe & Low 2002) measures adjacent-
sentence length contrast — the ordering that the Fano factor throws away.

liveness_summary composes nPVI with paragraph-motion variety and concrete-instance
density, minus an ornament penalty. The result is advisory telemetry, not a verdict;
qualitative judgement of improvement belongs to the reading-council A/B.
"""
from __future__ import annotations

import re


DEFAULT_MIN_WORDS = 4  # ignore fragments so "Yes." stuffing cannot inflate cadence


def _qualifying_lengths(text: str, min_words: int) -> list[int]:
    sents = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    lengths = [len(re.findall(r"[A-Za-z']+", s)) for s in sents]
    return [n for n in lengths if n >= min_words]


def npvi(text: str, min_words: int = DEFAULT_MIN_WORDS) -> float:
    """Normalized pairwise variability index of sentence lengths.

    0 means perfectly even; higher means more adjacent-pair contrast. Sentences with
    fewer than ``min_words`` words are dropped so fragment-stuffing cannot inflate the
    score.
    """
    lengths = _qualifying_lengths(text, min_words)
    if len(lengths) < 2:
        return 0.0
    total = 0.0
    pairs = 0
    for a, b in zip(lengths, lengths[1:]):
        denom = (a + b) / 2.0
        if denom > 0:
            total += abs(a - b) / denom
            pairs += 1
    if pairs == 0:
        return 0.0
    return round(100.0 * total / pairs, 2)
