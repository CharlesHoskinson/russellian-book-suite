"""Project a symbolic ingestion trace down to the ledger-row dict shape.

The exporter at skills/book-knowledge/scripts/export_symbolic_trace.py
emits one event per state transition. Phase 1 of the Bermuda verifier
only consumes the latest :verified state per claim, so this projection
flattens the trace into the same dict shape that the legacy
claims/ledger.jsonl reader produces.

Used by scripts/run_verification.py when
<workspace>/analysis/ingest-trace.edn is present.

REQ-TRACE-001, REQ-TRACE-002, REQ-TRACE-003: trace consumption + skip
non-verified + text backfill from proposed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts._edn_reader import Keyword, Symbol, read_edn


class TraceProjectionError(ValueError):
    """Raised when the trace file is missing or structurally invalid."""


def _strip(k: Any) -> str:
    if isinstance(k, Keyword):
        return str(k).lstrip(":")
    return str(k)


def read_trace(path: Path) -> dict:
    """Read an EDN trace file into a normalised dict.

    Returns:
        {"version": int, "book_id": str, "events": [{"head": str,
        "payload": dict}, ...]}.
    """
    if not path.exists():
        raise TraceProjectionError(f"trace file not found: {path}")
    edn = read_edn(path.read_text(encoding="utf-8"))
    version = edn.get(Keyword("version"))
    book_id = edn.get(Keyword("book/id"))
    raw = edn.get(Keyword("events"), [])
    events: list[dict] = []
    for entry in raw:
        if not isinstance(entry, list) or len(entry) < 2:
            continue
        head, payload = entry[0], entry[1]
        head_str = str(head) if isinstance(head, Symbol) else str(head).lstrip(":")
        flat = {_strip(k): v for k, v in payload.items()}
        events.append({"head": head_str, "payload": flat})
    return {"version": version, "book_id": book_id, "events": events}


def project_trace_to_ledger_rows(trace: dict) -> list[dict]:
    """Project the trace down to the per-claim row shape ingest_ledger expects.

    Strategy: gather the latest :proposed payload per claim (it carries
    :text and :confidence), then for every :verified event with a known
    claim/id emit one row marked status=verified with text + confidence
    backfilled from the proposed payload.
    """
    proposed: dict[str, dict] = {}
    rows: list[dict] = []
    for ev in trace.get("events", []):
        head = ev["head"]
        payload = ev["payload"]
        cid = payload.get("claim/id")
        if head == "claim/proposed" and cid:
            proposed[cid] = payload
        elif head == "claim/verified" and cid:
            seed = proposed.get(cid, {})
            text = payload.get("text") or seed.get("text", "")
            confidence = payload.get("confidence")
            if confidence is None:
                confidence = seed.get("confidence", 0.0)
            row = {
                "claim_id": cid,
                "claim_type": payload.get("claim_type")
                              or seed.get("claim_type")
                              or "fact",
                "canonical_text": text,
                "status": "verified",
                "confidence": float(confidence),
                "source_spans": payload.get("source/spans")
                                or seed.get("source/spans")
                                or [],
                "supports_chapters": payload.get("supports_chapters")
                                     or seed.get("supports_chapters")
                                     or [],
            }
            rows.append(row)
    return rows
