"""Abductive counter-claim generation for load-bearing claims."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .counter_claims import append_counter_claim, next_counter_claim_id
from .ledger import append_claim, read_claims
from .workspace import WorkspaceLayout

PROMPT_TEMPLATE = """\
Given a claim from a non-fiction book's ledger, generate the 2-3 strongest rival
hypotheses that, if true, would falsify or weaken the claim. Each rival must be:
- A single declarative sentence (no questions, no hedges, no lists).
- Tagged with exactly one disagreement vector from: mechanism, measurement,
  scope, time_period, population.

Claim text:
{claim_text}

Return JSON only, an array of objects with keys "text" and "disagreement_vector".
No prose outside the JSON.
"""


def prompt_for_claim(claim: dict) -> str:
    return PROMPT_TEMPLATE.format(claim_text=claim["canonical_text"])


def _latest_claim_record(workspace_root: Path, claim_id: str) -> dict | None:
    layout = WorkspaceLayout(workspace_root)
    found: dict | None = None
    for r in read_claims(layout):
        if r["claim_id"] == claim_id:
            found = r
    return found


def generate_for_claim(workspace_root: Path, claim_id: str,
                       llm_call: Callable[[str], str]) -> list[str]:
    target = _latest_claim_record(workspace_root, claim_id)
    if target is None:
        raise ValueError(f"claim not found: {claim_id}")
    prompt = prompt_for_claim(target)
    raw = llm_call(prompt)
    rivals = json.loads(raw)
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    new_ids: list[str] = []
    for rival in rivals:
        cc_id = next_counter_claim_id(workspace_root, reserved=set(new_ids))
        rec = {
            "id": cc_id,
            "target_claim_id": claim_id,
            "text": rival["text"],
            "disagreement_vector": rival["disagreement_vector"],
            "status": "open",
            "provenance": {"generator": "abduction-v1", "prompt_sha256": prompt_hash},
            "created_at": now,
            "addressed_in_chapter": None,
        }
        append_counter_claim(workspace_root, rec)
        new_ids.append(cc_id)
    # Append an updated claim record carrying the new counter_claim_ids so the
    # next ledger read picks them up. Route through append_claim so the schema
    # validator runs before the write — preserves append-only ledger semantics
    # and the schema-discipline invariant.
    layout = WorkspaceLayout(workspace_root)
    updated = dict(target)
    existing = list(updated.get("counter_claim_ids", []))
    updated["counter_claim_ids"] = existing + new_ids
    append_claim(layout, updated)
    return new_ids


def generate_for_all_load_bearing(workspace_root: Path,
                                  llm_call: Callable[[str], str]) -> dict[str, list[str]]:
    layout = WorkspaceLayout(workspace_root)
    latest: dict[str, dict] = {}
    for r in read_claims(layout):
        latest[r["claim_id"]] = r
    out: dict[str, list[str]] = {}
    for cid, rec in latest.items():
        if rec.get("load_bearing"):
            existing = set(rec.get("counter_claim_ids", []))
            if existing:
                continue
            out[cid] = generate_for_claim(workspace_root, cid, llm_call)
    return out


def pending_load_bearing(workspace_root: Path) -> list[dict]:
    """Latest load-bearing claim records that still have no counter-claims."""
    layout = WorkspaceLayout(workspace_root)
    latest: dict[str, dict] = {}
    for r in read_claims(layout):
        latest[r["claim_id"]] = r
    return [rec for rec in latest.values()
            if rec.get("load_bearing") and not rec.get("counter_claim_ids")]


def main(argv: list[str]) -> int:
    """Emit the abduction prompts for every load-bearing claim awaiting rivals.

    Counter-claim generation needs an LLM, which this skill does not bundle: the
    driving agent supplies the `llm_call` and feeds responses back through
    generate_for_claim (see the Bundle C runbook). This CLI does the offline half
    of that loop — it lists the pending claims and prints the exact prompt to run
    for each, so the documented command performs real, observable work.
    """
    parser = argparse.ArgumentParser(
        prog="python -m scripts.generate_counter_claims",
        description="Print abduction prompts for load-bearing claims lacking counter-claims.",
    )
    parser.add_argument("workspace", type=Path, help="Workspace root.")
    args = parser.parse_args(argv)
    pending = pending_load_bearing(args.workspace.resolve())
    for rec in pending:
        print(f"### {rec['claim_id']}")
        print(prompt_for_claim(rec))
        print()
    print(f"pending load-bearing claims: {len(pending)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
