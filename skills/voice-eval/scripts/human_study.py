# skills/voice-eval/scripts/human_study.py
"""Blind A/B human-study scaffold + signal-graduation gate (REQ-VEVAL-016/017).

Deterministic given a seed (the randomization uses a seeded ``random.Random``; the
running study is a later activity, but the scaffold and its statistics are built and
tested now). Fleiss' κ measures inter-rater reliability; graduation is gated on a
Spearman correlation whose bootstrap CI excludes zero and a non-negative
trustworthiness delta.
"""
from __future__ import annotations

import random

MIN_ITEMS = 50
GRADUATION_MIN_SPEARMAN = 0.4   # "moderate positive" floor (design § Component 6)


def build_study(pairs: list[dict], *, seed: int, rubric) -> dict:
    if len(pairs) < MIN_ITEMS:
        raise ValueError(f"human study needs >= {MIN_ITEMS} pairs, got {len(pairs)}")
    rng = random.Random(seed)
    items = []
    for pair in pairs:
        a_is_v1 = rng.random() < 0.5
        a_arm, b_arm = ("v1", "v2") if a_is_v1 else ("v2", "v1")
        items.append({
            "prompt_id": pair["prompt_id"],
            "key": {"A": a_arm, "B": b_arm},                 # recoverable mapping (kept by the runner)
            "sides": {"A": {"text": pair[a_arm]}, "B": {"text": pair[b_arm]}},
        })
    rng.shuffle(items)
    return {"items": items, "rubric": tuple(rubric), "min_items": MIN_ITEMS}


def fleiss_kappa(table: list[dict]) -> float:
    """table[item] = {category: n_raters_choosing_it}. All items must share the rater count."""
    categories = sorted({c for row in table for c in row})
    n = sum(table[0].values())
    N = len(table)
    p_j = {c: sum(row.get(c, 0) for row in table) / (N * n) for c in categories}
    P_i = []
    for row in table:
        s = sum(row.get(c, 0) ** 2 for c in categories) - n
        P_i.append(s / (n * (n - 1)))
    P_bar = sum(P_i) / N
    P_e = sum(v * v for v in p_j.values())
    if P_e == 1.0:
        return 1.0
    return (P_bar - P_e) / (1 - P_e)


def graduate(*, spearman: float, ci: tuple[float, float], trust_delta: float) -> dict:
    reasons = {
        "moderate_positive": spearman >= GRADUATION_MIN_SPEARMAN,
        "ci_excludes_zero": ci[0] > 0.0,
        "trust_not_degraded": trust_delta >= 0.0,
    }
    return {"graduates": all(reasons.values()), "reasons": reasons}
