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
