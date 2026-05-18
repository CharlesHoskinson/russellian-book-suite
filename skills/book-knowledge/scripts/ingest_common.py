"""Shared helpers for source ingestion (manifest writing, log appends)."""
from __future__ import annotations

from datetime import datetime, timezone

from .workspace import WorkspaceLayout


def append_log_entry(layout: WorkspaceLayout, action: str, doc_id: str, summary: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    entry = f"\n## [{timestamp}] {action} | {doc_id}\n{summary}\n"
    with layout.wiki_log.open("a", encoding="utf-8") as fh:
        fh.write(entry)
