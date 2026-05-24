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


_VALID_VECTORS = {"mechanism", "measurement", "scope", "time_period", "population"}


def _strip_code_fence(raw: str) -> str:
    """Strip leading/trailing markdown code fences (```json ... ```)."""
    stripped = raw.strip()
    if stripped.startswith("```"):
        # Remove the opening fence line (e.g. ```json or just ```)
        first_newline = stripped.find("\n")
        if first_newline != -1:
            stripped = stripped[first_newline + 1:]
        # Remove the closing fence
        if stripped.endswith("```"):
            stripped = stripped[: stripped.rfind("```")].rstrip()
    return stripped


def _normalize_disagreement_vector(val: object) -> str:
    """Coerce model output to a valid disagreement_vector string.

    The model sometimes emits an array of ints or an unexpected string.
    Fall back to 'mechanism' if nothing maps cleanly.
    """
    if isinstance(val, str) and val in _VALID_VECTORS:
        return val
    # Try to infer from string partial match
    if isinstance(val, str):
        lower = val.lower()
        for v in _VALID_VECTORS:
            if v in lower:
                return v
    return "mechanism"


def generate_for_claim(workspace_root: Path, claim_id: str,
                       llm_call: Callable[[str], str]) -> list[str]:
    target = _latest_claim_record(workspace_root, claim_id)
    if target is None:
        raise ValueError(f"claim not found: {claim_id}")
    prompt = prompt_for_claim(target)
    raw = llm_call(prompt)
    rivals = json.loads(_strip_code_fence(raw))
    for rival in rivals:
        rival["disagreement_vector"] = _normalize_disagreement_vector(
            rival.get("disagreement_vector")
        )
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
    # Append an updated claim record carrying the new counter_claim_ids so the
    # next ledger read picks them up. Preserves append-only ledger semantics.
    layout = WorkspaceLayout(workspace_root)
    updated = dict(target)
    existing = list(updated.get("counter_claim_ids", []))
    updated["counter_claim_ids"] = existing + new_ids
    with layout.ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(updated, sort_keys=True) + "\n")
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


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.generate_counter_claims",
        description="Generate abductive counter-claims for load-bearing claims.",
    )
    parser.add_argument("workspace", type=Path, help="Workspace root.")
    parser.add_argument(
        "--claim-id",
        default=None,
        help="Generate counter-claims for a single claim ID only. "
             "Omit to process all load-bearing claims without existing counter-claims.",
    )
    parser.add_argument(
        "--llm-backend",
        choices=["subagent", "ollama"],
        default="subagent",
        help="LLM dispatch backend. subagent (default): existing behavior. "
             "ollama: route through llm_infra via production_llm.default_llm_call().",
    )
    parser.add_argument(
        "--model",
        default="gemma4:31b",
        help="Ollama model (only used when --llm-backend=ollama).",
    )
    parser.add_argument(
        "--num-predict",
        type=int,
        default=None,
        help="Caps Ollama output tokens (only used when --llm-backend=ollama). "
             "None = use frontmatter or default.",
    )
    args = parser.parse_args(argv)

    if args.llm_backend == "ollama":
        # Import lazily — keeps subagent path free of llm_infra dependency at import time
        if args.num_predict is not None:
            from llm_infra import make_ollama_call
            llm_call = make_ollama_call(model=args.model, num_predict=args.num_predict)
        else:
            from scripts.production_llm import default_llm_call
            llm_call = default_llm_call(model=args.model)
    else:
        # subagent path: existing behavior — llm_call must be provided externally.
        # For CLI invocation without ollama, fall back to production_llm (subagent wrapper).
        from scripts.production_llm import default_llm_call
        llm_call = default_llm_call()

    workspace = args.workspace.resolve()
    if args.claim_id:
        new_ids = generate_for_claim(workspace, args.claim_id, llm_call)
        print(f"generated {len(new_ids)} counter-claim(s) for {args.claim_id}: {new_ids}")
    else:
        result = generate_for_all_load_bearing(workspace, llm_call)
        total = sum(len(v) for v in result.values())
        print(f"generated {total} counter-claim(s) across {len(result)} claim(s)")
        for cid, ids in result.items():
            print(f"  {cid}: {ids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
