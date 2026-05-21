"""Append-only JSONL ledger I/O for the corpus build pipeline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    """Append one JSON object as a single line. Creates the file and parents if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
        fh.write("\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file. Returns [] if the file does not exist."""
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def read_index(path: Path) -> dict[str, Any]:
    """Read the russellian-style corpus index.json."""
    return json.loads(path.read_text(encoding="utf-8"))


def append_index_entries(path: Path, new_entries: list[dict[str, Any]]) -> None:
    """Append new paragraph entries to index.json and update paragraph_count.

    Existing entries are preserved verbatim. Writes atomically via tempfile rename.
    Raises ValueError if any new entry's id already exists in the index OR collides
    with another id in new_entries itself. Validation happens before any write,
    so a partial failure leaves the index untouched.
    """
    idx = read_index(path)
    existing_ids = {e["id"] for e in idx["paragraphs"]}
    seen_in_batch: set[str] = set()
    for entry in new_entries:
        if entry["id"] in existing_ids or entry["id"] in seen_in_batch:
            raise ValueError(f"entry id {entry['id']!r} already exists in {path}")
        seen_in_batch.add(entry["id"])
    idx["paragraphs"].extend(new_entries)
    idx["paragraph_count"] = len(idx["paragraphs"])
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
