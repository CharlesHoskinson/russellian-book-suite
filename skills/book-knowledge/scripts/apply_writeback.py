"""Apply proposed transitions emitted by book-qa propose_writeback."""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from .io_utils import read_jsonl
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
    proposed = read_jsonl(pt)
    applied = 0
    op = _operator()
    for p in proposed:
        if not auto_apply:
            continue
        # REQ-QA-PIPE-012: :requires :human-review blocks auto-apply per proposal.
        if p.get("requires") == "human-review" or p.get("auto_apply") is False:
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


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.apply_writeback",
        description="Apply proposed-transitions from book-qa to the claim ledger "
                    "and counter-claim records.",
        usage="python -m scripts.apply_writeback <workspace> [--auto-apply]",
    )
    parser.add_argument("workspace", type=Path, help="Workspace root.")
    parser.add_argument(
        "--auto-apply", action="store_true",
        help="Actually apply transitions (default: dry-run that only reports counts).",
    )
    args = parser.parse_args(argv)
    summary = apply_writeback(args.workspace.resolve(), auto_apply=args.auto_apply)
    mode = "auto-apply" if args.auto_apply else "dry-run"
    print(f"writeback ({mode}): proposed={summary['proposed']} applied={summary['applied']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
