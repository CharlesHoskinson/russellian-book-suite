"""Deterministic stratified sampling of discovered video rows."""

from __future__ import annotations

import random
import re
from typing import Any

_YEAR_AT_START = re.compile(r"^\s*(\d{4})\b")


def publish_year(published: object) -> str:
    """Return a 4-digit year if `published` begins with one (ISO date or bare year), else 'unknown'.

    The channel grid yields relative strings ("2 years ago"); those have no real year and
    must not be mislabeled. Live runs should enrich rows with yt-dlp upload_date first.
    """
    m = _YEAR_AT_START.match(str(published))
    return m.group(1) if m else "unknown"

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
    return (publish_year(row["published"]), infer_format(row), length_bucket(row["duration_seconds"]))


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
