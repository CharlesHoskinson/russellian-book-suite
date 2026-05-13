"""Shared I/O helpers for append-only JSONL ledgers."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable

_log = logging.getLogger(__name__)


def read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file, skipping blank lines and warning on corruption.

    A single malformed line does not abort the read. The corrupt line is
    skipped with a warning logged to the module logger. Returns the list of
    well-formed records in file order. Returns [] if the file does not exist.
    """
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
            _log.warning(
                "skipping malformed JSONL line %d in %s: %s; content=%r",
                i, path, e, line[:80],
            )
    return out


def latest_per(records: Iterable[dict], key: str) -> dict[str, dict]:
    """Return the last-write-wins mapping over `records` keyed by `key`.

    Later records in iteration order overwrite earlier ones. The returned
    dict's iteration order matches the order of first appearance — useful
    when callers want a stable order.
    """
    latest: dict[str, dict] = {}
    for r in records:
        if key in r:
            latest[r[key]] = r
    return latest
