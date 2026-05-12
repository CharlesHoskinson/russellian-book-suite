"""Slice the claim ledger for a single chapter, honouring contract filters."""
from __future__ import annotations

import json
from pathlib import Path


def _latest_per_claim_from_ledger(workspace_root: Path) -> list[dict]:
    """Read ledger.jsonl and return the last record seen for each claim_id."""
    ledger = Path(workspace_root) / "claims" / "ledger.jsonl"
    if not ledger.exists():
        return []
    latest: dict[str, dict] = {}
    for line in ledger.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        latest[rec["claim_id"]] = rec
    return list(latest.values())


def slice_for_chapter(workspace_root: Path, chapter_id: str, contract: dict) -> list[dict]:
    """Return claim records from the ledger that are relevant to chapter_id.

    Filtering rules:
    - Only records whose supports_chapters includes chapter_id.
    - refuted claims are excluded unless their claim_id appears in
      contract["force_include_refuted"].
    - disputed claims are excluded unless contract["accept_disputed"] is True.
    - superseded claims are always excluded.
    """
    records = _latest_per_claim_from_ledger(workspace_root)
    force_include = set(contract.get("force_include_refuted", []))
    accept_disputed = bool(contract.get("accept_disputed", False))
    out: list[dict] = []
    for r in records:
        if chapter_id not in r.get("supports_chapters", []):
            continue
        status = r.get("status", "")
        if status == "refuted" and r["claim_id"] not in force_include:
            continue
        if status == "disputed" and not accept_disputed:
            continue
        if status == "superseded":
            continue
        out.append(r)
    return out
