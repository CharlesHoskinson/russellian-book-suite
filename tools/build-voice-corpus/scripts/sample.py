"""Deterministic stratified sampling of discovered video rows."""

from __future__ import annotations

import random
from typing import Any

_FORMAT_KEYWORDS = [
    ("ama", ("ama", "ask me anything", "q&a", "surprise")),
    ("whiteboard", ("whiteboard",)),
    ("keynote", ("keynote", "summit", "conference", "talk")),
]


def infer_format(row: dict[str, Any]) -> str:
    title = row["title"].lower()
    for fmt, keys in _FORMAT_KEYWORDS:
        if any(k in title for k in keys):
            return fmt
    return "short" if row["duration_seconds"] < 600 else "monologue"


def length_bucket(duration_seconds: int) -> str:
    if duration_seconds < 300:
        return "xs"
    if duration_seconds < 900:
        return "s"
    if duration_seconds < 1800:
        return "m"
    if duration_seconds < 3600:
        return "l"
    return "xl"


def stratum_key(row: dict[str, Any]) -> tuple[str, str, str]:
    year = str(row["published"])[:4]
    return (year, infer_format(row), length_bucket(row["duration_seconds"]))


def sample(rows: list[dict[str, Any]], *, target: int, seed: int) -> list[dict[str, Any]]:
    """Round-robin across strata under a fixed seed until `target` rows are chosen."""
    rng = random.Random(seed)
    strata: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        strata.setdefault(stratum_key(row), []).append(row)
    for bucket in strata.values():
        bucket.sort(key=lambda r: r["video_id"])
        rng.shuffle(bucket)
    ordered_keys = sorted(strata.keys())
    rng.shuffle(ordered_keys)
    picked: list[dict[str, Any]] = []
    exhausted = False
    while len(picked) < target and not exhausted:
        exhausted = True
        for key in ordered_keys:
            bucket = strata[key]
            if bucket:
                picked.append(bucket.pop())
                exhausted = False
                if len(picked) >= target:
                    break
    return picked
