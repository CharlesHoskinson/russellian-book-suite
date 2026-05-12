"""Abductive counter-claim generation for load-bearing claims."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .counter_claims import append_counter_claim, next_counter_claim_id
from .ledger import read_claims
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
        cc_id = next_counter_claim_id(workspace_root)
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
