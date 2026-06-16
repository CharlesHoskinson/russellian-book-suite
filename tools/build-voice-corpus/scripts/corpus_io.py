"""Read/write the russellian-style corpus index.json envelope."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def init_index(path: Path, *, version: str, copyright_policy: str, sources: dict[str, Any]) -> None:
    """Create an empty corpus index with the standard envelope if it does not exist."""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    envelope = {
        "version": version,
        "paragraph_count": 0,
        "copyright_policy": copyright_policy,
        "sources": sources,
        "paragraphs": [],
    }
    path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")


def read_index(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def append_index_entries(path: Path, new_entries: list[dict[str, Any]]) -> None:
    """Append entries, update paragraph_count, reject id collisions. Atomic via tmp rename."""
    idx = read_index(path)
    existing = {e["id"] for e in idx["paragraphs"]}
    seen: set[str] = set()
    for entry in new_entries:
        eid = entry["id"]
        if eid in existing or eid in seen:
            raise ValueError(f"entry id {eid!r} already exists")
        seen.add(eid)
    idx["paragraphs"].extend(new_entries)
    idx["paragraph_count"] = len(idx["paragraphs"])
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
