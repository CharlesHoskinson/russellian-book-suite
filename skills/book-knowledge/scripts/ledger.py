"""Append-only claim ledger with state-machine-aware transitions."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from .belief_graph import prior_for_status
from .claim_validator import (
    validate_claim, assert_transition_allowed, ClaimValidationError,
)
from .events_log import append_event
from .io_utils import read_jsonl
from .workspace import WorkspaceLayout


class LedgerError(Exception):
    pass


def read_claims(layout: WorkspaceLayout) -> list[dict]:
    return read_jsonl(layout.ledger)


def latest_status(layout: WorkspaceLayout, claim_id: str) -> str | None:
    found: str | None = None
    for record in read_claims(layout):
        if record["claim_id"] == claim_id:
            found = record["status"]
    return found


def next_claim_id(layout: WorkspaceLayout) -> str:
    year = datetime.now(timezone.utc).year
    prefix = f"clm-{year}-"
    existing = [c["claim_id"] for c in read_claims(layout) if c["claim_id"].startswith(prefix)]
    next_num = (max((int(cid.rsplit("-", 1)[1]) for cid in existing), default=0)) + 1
    return f"{prefix}{next_num:06d}"


def append_claim(layout: WorkspaceLayout, record: dict) -> None:
    try:
        validate_claim(record)
    except ClaimValidationError as e:
        raise LedgerError(f"claim validation failed: {e}") from e
    with layout.ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def transition_status(layout: WorkspaceLayout, claim_id: str, new_status: str,
                      cause_ticket_id: str = "manual",
                      cause_class: str = "manual",
                      operator: str = "unknown",
                      note: str = "") -> dict:
    current = latest_status(layout, claim_id)
    if current is None:
        raise LedgerError(f"unknown claim_id: {claim_id}")
    try:
        assert_transition_allowed(current, new_status)
    except ClaimValidationError as e:
        raise LedgerError(str(e)) from e

    base: dict | None = None
    for record in read_claims(layout):
        if record["claim_id"] == claim_id:
            base = record

    new_record = dict(base)  # type: ignore[arg-type]
    new_record["status"] = new_status
    new_record["p_prior"] = prior_for_status(new_status)
    new_record["last_verified_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if note:
        new_record["review_notes"] = note
    append_claim(layout, new_record)

    append_event(layout.root, {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "claim_id": claim_id,
        "from": current,
        "to": new_status,
        "cause_ticket_id": cause_ticket_id,
        "cause_class": cause_class,
        "operator": operator,
    })

    return new_record
