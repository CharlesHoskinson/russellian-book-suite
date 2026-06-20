# skills/voice-eval/scripts/winrate.py
"""Pairwise win-rate with a Wilson score confidence interval (REQ-VEVAL-012)."""
from __future__ import annotations

import math

Z_95 = 1.959963984540054


def wilson_interval(wins: float, n: int, z: float = Z_95) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    phat = wins / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    margin = (z / denom) * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))
    return (max(0.0, center - margin), min(1.0, center + margin))


def win_rate(ballots: list[dict], *, target: str = "v2") -> dict:
    """Each filled ballot contributes one judgment: 1 if the kept arm == target, else 0.
    (Order-swap duplicates are counted independently, per the design's order-swapped run.)"""
    wins = 0.0
    n = 0
    for b in ballots:
        v = b.get("verdict")
        if not v or "keep" not in v:
            continue
        kept_arm = b[v["keep"]]["arm"]
        wins += 1.0 if kept_arm == target else 0.0
        n += 1
    rate = wins / n if n else 0.0
    lo, hi = wilson_interval(wins, n)
    return {"target": target, "wins": wins, "n": n, "rate": rate, "ci_low": lo, "ci_high": hi}
