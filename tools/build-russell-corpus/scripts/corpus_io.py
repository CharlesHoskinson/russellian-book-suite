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


def content_locator(paragraph_text: str) -> str:
    """First 120 stripped characters of a paragraph — authoritative position locator.

    Used to find a paragraph in source even when line numbers drift across editions.
    """
    return paragraph_text.strip()[:120]


def paragraph_in_source(paragraph_text: str, source_path: Path) -> bool:
    """True iff the paragraph appears verbatim in the cached source file.

    The check is conservative: the locator (first 120 chars stripped, whitespace-normalised)
    must appear in the whitespace-normalised source, AND the full paragraph (whitespace-
    normalised) must also appear. Both checks operate against the whitespace-normalised
    source so that line-wrapped HTML paragraphs are matched correctly.
    """
    source = source_path.read_text(encoding="utf-8")
    normalised_source = " ".join(source.split())
    normalised_locator = " ".join(content_locator(paragraph_text).split())
    if normalised_locator not in normalised_source:
        return False
    normalised_para = " ".join(paragraph_text.split())
    return normalised_para in normalised_source


def find_paragraph_line(locator: str, source_path: Path) -> int | None:
    """Return the 1-indexed line number where the locator first appears, or None.

    The locator (up to 120 chars) routinely straddles physical line breaks because real
    Gutenberg HTML wraps paragraphs at ~70 chars. A raw per-line substring test would miss
    every wrapped paragraph, so we match against a whitespace-normalised view consistent
    with paragraph_in_source: the locator is whitespace-normalised, and we accumulate the
    normalised text line by line, returning the 1-indexed line at which the running
    normalised buffer first contains the locator.
    """
    normalised_locator = " ".join(locator.split())
    if not normalised_locator:
        return None
    buffer = ""
    with source_path.open("r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, start=1):
            buffer = (buffer + " " + line).strip() if buffer else line
            buffer = " ".join(buffer.split())
            if normalised_locator in buffer:
                return i
            # Keep only the tail long enough to still match a locator that began on an
            # earlier line, bounding memory for large sources.
            if len(buffer) > 2 * len(normalised_locator):
                buffer = buffer[-2 * len(normalised_locator):]
    return None


def sha256_hex(text: str) -> str:
    """Hex SHA-256 of UTF-8 text — used for dedup keys."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
