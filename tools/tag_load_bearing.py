#!/usr/bin/env python
"""One-shot: mark claims as load_bearing=true based on cross-chapter citations.

Usage:
    python tools/tag_load_bearing.py <workspace>

Treats any claim referenced by 2+ chapters via supports_chapters as load-bearing.
Appends an updated record with load_bearing=true to the ledger (append-only).
Idempotent — already-tagged load-bearing claims are skipped.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def tag_load_bearing(workspace_root: Path, min_chapters: int = 2) -> int:
    ledger = workspace_root / "claims" / "ledger.jsonl"
    if not ledger.exists():
        print(f"no ledger at {ledger}", file=sys.stderr)
        return 0
    records = [json.loads(l) for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not records:
        return 0

    # Tally distinct chapter citations per claim.
    chapter_count_by_claim: dict[str, set[str]] = {}
    for r in records:
        for ch in r.get("supports_chapters", []):
            chapter_count_by_claim.setdefault(r["claim_id"], set()).add(ch)

    # Latest record per claim_id.
    latest: dict[str, dict] = {}
    for r in records:
        latest[r["claim_id"]] = r

    load_bearing_ids = {cid for cid, chs in chapter_count_by_claim.items()
                        if len(chs) >= min_chapters}

    tagged = 0
    with ledger.open("a", encoding="utf-8") as fh:
        for cid in sorted(load_bearing_ids):
            if latest[cid].get("load_bearing"):
                continue  # already tagged
            updated = dict(latest[cid])
            updated["load_bearing"] = True
            fh.write(json.dumps(updated, sort_keys=True) + "\n")
            tagged += 1
    return tagged


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: tag_load_bearing.py <workspace>", file=sys.stderr)
        return 2
    ws = Path(argv[1])
    n = tag_load_bearing(ws)
    print(f"tagged {n} claims as load_bearing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
