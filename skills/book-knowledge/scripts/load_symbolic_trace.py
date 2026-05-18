# skills/book-knowledge/scripts/load_symbolic_trace.py
"""Load a symbolic ingestion trace from EDN into a structured Python dict.

The on-disk trace has the shape:

    {:version 1
     :book/id "..."
     :events [(head/sym {...payload}) ...]}

This loader normalises that into a plain Python dict:

    {
      "version": 1,
      "book_id": "...",
      "events": [
        {"head": "source/ingested",
         "payload": {"doc/id": "...", "ingested-at": datetime(...), ...}},
        ...
      ],
    }

Keyword keys in the payload are flattened to their string form ("doc/id"
without the leading colon) so downstream consumers can use plain dict
access. The schema at ingest-trace.schema.json is enforced.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

# scripts/__init__.py extends the package path to include neurosym-forge's
# scripts/, so the imports below resolve to the correct forge modules.
from scripts._edn_reader import Keyword, Symbol, read_edn  # noqa: E402

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "assets" / "ingest-trace.schema.json"


def _flatten_key(k: Any) -> str:
    if isinstance(k, Keyword):
        return str(k).lstrip(":")
    return str(k)


def _flatten_payload(payload: dict) -> dict:
    return {_flatten_key(k): v for k, v in payload.items()}


def load_trace(path: Path) -> dict:
    """Parse the EDN trace file at `path` and validate against the schema."""
    edn = read_edn(path.read_text(encoding="utf-8"))
    version = edn.get(Keyword("version"))
    book_id = edn.get(Keyword("book/id"))
    raw_events = edn.get(Keyword("events"), [])
    events = []
    for entry in raw_events:
        if not isinstance(entry, list) or len(entry) < 2:
            continue
        head, payload = entry[0], entry[1]
        head_str = str(head) if isinstance(head, Symbol) else str(head).lstrip(":")
        events.append({"head": head_str, "payload": _flatten_payload(payload)})
    result = {"version": version, "book_id": book_id, "events": events}

    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(result, schema)
    except jsonschema.ValidationError as e:
        raise ValueError(f"trace fails schema validation: {e.message}") from e
    return result
