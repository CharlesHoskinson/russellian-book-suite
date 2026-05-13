"""Promote counter-claims from 'open' to 'addressed' based on check_address verdicts."""
from __future__ import annotations

from pathlib import Path

from .counter_claims import append_counter_claim, read_counter_claims
from .io_utils import latest_per


def promote_addressed(workspace_root: Path, chapter_id: str,
                      addressed_ids: list[str]) -> int:
    items = read_counter_claims(workspace_root)
    latest = latest_per(items, "id")
    promoted = 0
    for cc_id in addressed_ids:
        rec = latest.get(cc_id)
        if rec is None or rec["status"] == "addressed":
            continue
        new = dict(rec)
        new["status"] = "addressed"
        new["addressed_in_chapter"] = chapter_id
        append_counter_claim(workspace_root, new)
        promoted += 1
    return promoted
