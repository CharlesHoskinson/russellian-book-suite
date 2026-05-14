"""Pairwise contradiction detection across verified claims.

Heuristic: two claims conflict if they share content vocabulary and
contain antonym pairs (allowed/forbidden, mandatory/optional, etc.).
This is a coarse first pass.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from itertools import combinations

from .ledger import read_claims, transition_status
from .workspace import WorkspaceLayout

ANTONYM_PAIRS = [
    ("allowed", "forbidden"), ("mandatory", "optional"),
    ("required", "not required"), ("supported", "unsupported"),
    ("present", "absent"), ("succeed", "fail"),
    ("possible", "impossible"), ("safe", "unsafe"),
]


def _verified_only(records: list[dict]) -> list[dict]:
    latest: dict[str, dict] = {}
    for r in records:
        latest[r["claim_id"]] = r
    return [r for r in latest.values() if r["status"] == "verified"]


def _stem_words(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{4,}", text.lower()))


def _antonym_overlap(a: str, b: str) -> bool:
    a_low, b_low = a.lower(), b.lower()
    for x, y in ANTONYM_PAIRS:
        if (x in a_low and y in b_low) or (y in a_low and x in b_low):
            return True
    return False


def detect_conflicts(layout: WorkspaceLayout) -> list[dict]:
    verified = _verified_only(read_claims(layout))
    conflicts: list[dict] = []
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for a, b in combinations(verified, 2):
        words_a = _stem_words(a["canonical_text"])
        words_b = _stem_words(b["canonical_text"])
        if len(words_a & words_b) >= 1 and _antonym_overlap(a["canonical_text"], b["canonical_text"]):
            conflicts.append({
                "conflict_id": f"cg-{len(conflicts) + 1:04d}",
                "claims": [a["claim_id"], b["claim_id"]],
                "reason": "antonym pair detected with shared subject vocabulary",
                "detected_at": timestamp,
            })

    if conflicts:
        with layout.conflicts.open("a", encoding="utf-8") as fh:
            for c in conflicts:
                fh.write(json.dumps(c, sort_keys=True) + "\n")

        conflicting_ids: set[str] = set()
        for c in conflicts:
            conflicting_ids.update(c["claims"])
        for claim_id in sorted(conflicting_ids):
            transition_status(
                layout, claim_id, "disputed",
                cause_class="detect_conflicts",
                note="Antonym-pair conflict detected with another claim.",
            )

    return conflicts
