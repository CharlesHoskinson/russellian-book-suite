"""Slice the claim ledger for a single chapter, honouring contract filters."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from .sibling_skills import SiblingNotFoundError, load_book_knowledge_module

_log = logging.getLogger(__name__)


def _read_jsonl_local(path: Path) -> list[dict]:
    """Fallback JSONL reader used when the book-knowledge sibling is not installed."""
    if not path.exists():
        return []
    out: list[dict] = []
    for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            _log.warning("skipping malformed JSONL line %d in %s: %s", i, path, e)
    return out


def _latest_per_claim_from_ledger(workspace_root: Path) -> list[dict]:
    """Read ledger.jsonl and return the last record seen for each claim_id."""
    ledger = Path(workspace_root) / "claims" / "ledger.jsonl"
    try:
        io = load_book_knowledge_module("io_utils")
        return list(io.latest_per(io.read_jsonl(ledger), "claim_id").values())
    except SiblingNotFoundError:
        records = _read_jsonl_local(ledger)
        latest: dict[str, dict] = {}
        for r in records:
            latest[r["claim_id"]] = r
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
