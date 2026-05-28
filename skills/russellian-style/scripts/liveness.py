"""Order-sensitive liveness signals (stdlib only; no spaCy, no lint_common).

nPVI (normalized pairwise variability index; Grabe & Low 2002) measures adjacent-
sentence length contrast — the ordering that the Fano factor throws away.

``liveness_summary`` composes nPVI with paragraph-motion variety and concrete-instance
density, minus an ornament penalty, as advisory telemetry — not a verdict; the
reading-council A/B is the judge of whether the writing is actually livelier.
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


# --- Composite (advisory telemetry; not a verdict) ----------------------------------

# Normalization constants are calibration parameters, not thresholds. nPVI in the
# 50-80 band is "lively" per the prose-rhythm literature (Grabe & Low 2002 applied
# to sentence lengths); 60 is the midpoint. Concrete-density 8/1000 is the upper
# practical band observed in Russell's analytic prose. Ornament penalty caps at 0.5
# so a single decoration finding cannot zero out an otherwise lively passage.
_CADENCE_DENOM = 60.0
_CONCRETE_DENOM = 8.0
_ORNAMENT_DENOM = 10.0
_ORNAMENT_CAP = 0.5


def liveness_summary(npvi_value: float, motion_variety: float,
                     concrete_per_1000: float, ornament_per_1000: float) -> dict:
    """Compose advisory liveness telemetry. Not a verdict.

    Components normalize to roughly 0..1; ornament subtracts. ``motion_variety`` is
    expected in [0, 1] (fraction of distinct paragraph shapes); the other three
    inputs are raw measurements that the function normalises internally.
    The numbers describe; the reading-council A/B judges whether the writing is
    actually livelier.
    """
    cadence = round(min(max(npvi_value, 0.0) / _CADENCE_DENOM, 1.0), 3)
    motion = round(min(max(motion_variety, 0.0), 1.0), 3)
    concreteness = round(min(max(concrete_per_1000, 0.0) / _CONCRETE_DENOM, 1.0), 3)
    penalty = round(min(max(ornament_per_1000, 0.0) / _ORNAMENT_DENOM, _ORNAMENT_CAP), 3)
    liveness = round(max(0.0, (cadence + motion + concreteness) / 3.0 - penalty), 3)
    return {
        "metric": "liveness",
        "liveness": liveness,
        "components": {
            "cadence": cadence,
            "motion": motion,
            "concreteness": concreteness,
            "ornament_penalty": penalty,
        },
        "advisory": True,
    }
