"""Read QA tickets, propose ledger transitions; write to claims/ and qa/ reports."""
from __future__ import annotations

import json
from pathlib import Path

from .transition_rules import map_ticket_to_proposed_transition


def _load_tickets(qa_dir: Path) -> list[dict]:
    tickets: list[dict] = []
    for name in ("lint-findings.json", "swarm-findings.json"):
        p = qa_dir / name
        if not p.exists():
            continue
        payload = json.loads(p.read_text(encoding="utf-8"))
        tickets.extend(payload.get("tickets", []))
    return tickets


def propose_writeback(workspace_root: Path, version: str) -> Path:
    """Emit proposed ledger transitions from current QA findings.

    The output file `claims/proposed-transitions.jsonl` is OVERWRITTEN on each
    call — it is a per-build scratch artifact, not an accumulating log.
    Consumers (`apply_writeback.py`) must process it before the next sentinel
    run, or earlier proposals are lost.
    """
    qa_dir = workspace_root / "qa"
    claims_dir = workspace_root / "claims"
    claims_dir.mkdir(parents=True, exist_ok=True)
    tickets = _load_tickets(qa_dir)
    proposed: list[dict] = []
    for t in tickets:
        m = map_ticket_to_proposed_transition(t)
        if m is not None:
            m["severity"] = t.get("severity", "important")
            proposed.append(m)
    out_jsonl = claims_dir / "proposed-transitions.jsonl"
    # Intentional truncate-and-write: per-build scratch, consumed by apply_writeback.
    with out_jsonl.open("w", encoding="utf-8") as fh:
        for p in proposed:
            fh.write(json.dumps(p, sort_keys=True) + "\n")
    md_lines = [f"# Ledger writeback proposals — {version}", "",
                f"Total: {len(proposed)} proposed transition(s).", ""]
    md_lines.append("| kind | target | from→to / new_status | ticket | severity |")
    md_lines.append("|---|---|---|---|---|")
    for p in proposed:
        if p["kind"] == "claim":
            md_lines.append(f"| claim | {p['claim_id']} | {p['from']}→{p['to']} | {p['cause_ticket_id']} | {p['severity']} |")
        else:
            md_lines.append(f"| counter_claim | {p['counter_claim_id']} | →{p['new_status']} | {p['cause_ticket_id']} | {p['severity']} |")
    out_md = qa_dir / f"ledger-writeback-{version}.md"
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return out_md
