"""EDN/JSON read-write and checksum helpers.

For v0.1, we serialize the atomspace as JSON-compatible Python dicts and
write the file with a `.edn` extension. The scaffolded project's CLJS
reader parses EDN natively; this skill only round-trips structured data.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def read_edn_as_json(path: Path) -> Any:
    """Read an EDN-extension file written by write_json_as_edn."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_as_edn(path: Path, payload: Any) -> None:
    """Write a JSON-compatible payload to disk with stable formatting.

    Keys are sorted; indent is 2; encoding is UTF-8 with LF line endings.
    Keyword strings (":foo") are preserved verbatim in JSON; the scaffolded
    CLJS reader treats them as EDN keywords.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def file_checksum(path: Path) -> str:
    """SHA-256 hex digest of a file's bytes."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()
