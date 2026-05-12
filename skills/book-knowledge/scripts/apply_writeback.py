"""Apply proposed transitions emitted by book-qa propose_writeback."""
from __future__ import annotations

import getpass
import json
from pathlib import Path

from .ledger import transition_status
from .counter_claims import append_counter_claim, read_counter_claims
from .workspace import WorkspaceLayout


def _operator() -> str:
    try:
        user = getpass.getuser()
    except Exception:
        user = "unknown"
    return f"{user}@apply_writeback"


def apply_writeback(workspace_root: Path, auto_apply: bool = False) -> dict:
    layout = WorkspaceLayout(workspace_root)
    pt = layout.root / "claims" / "proposed-transitions.jsonl"
    if not pt.exists():
        return {"proposed": 0, "applied": 0}
    proposed: list[dict] = []
    for line in pt.read_text(encoding="utf-8").splitlines():
        if line.strip():
            proposed.append(json.loads(line))
    applied = 0
    op = _operator()
    for p in proposed:
        if not auto_apply:
            continue
        if p["kind"] == "claim":
            if p.get("severity") != "critical":
                continue
            if p.get("cause_class") != "unsupported_claim":
                continue
            transition_status(
                layout, p["claim_id"], p["to"],
                cause_ticket_id=p["cause_ticket_id"],
                cause_class=p["cause_class"],
                operator=op,
            )
            applied += 1
        elif p["kind"] == "counter_claim":
            existing = [c for c in read_counter_claims(workspace_root)
                        if c["id"] == p["counter_claim_id"]]
            if not existing:
                continue
            new = dict(existing[-1])
            new["status"] = p["new_status"]
            new["addressed_in_chapter"] = p.get("chapter_id")
            append_counter_claim(workspace_root, new)
            applied += 1
    return {"proposed": len(proposed), "applied": applied}
