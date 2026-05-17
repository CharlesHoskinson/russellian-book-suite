"""File I/O for atomspace EDN and rule files.

Uses the project's own EDN reader/writer (scripts/_edn_reader,
scripts/_edn_writer) so the .edn extension actually carries EDN syntax
that ClojureScript's reader can parse.

The legacy read_edn_as_json / write_json_as_edn shims remain as
deprecated aliases for one cycle to give callers room to migrate.
"""
from __future__ import annotations

import hashlib
import warnings
from pathlib import Path
from typing import Any

from scripts._edn_reader import read_edn
from scripts._edn_writer import write_edn


def read_edn_file(path: Path) -> Any:
    """Parse an EDN file from disk."""
    return read_edn(path.read_text(encoding="utf-8"))


def write_edn_file(path: Path, payload: Any) -> None:
    """Write a Python value to disk as pretty-printed EDN."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = write_edn(payload, pretty=True)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def file_checksum(path: Path) -> str:
    """SHA-256 hex digest of a file's bytes."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


# Deprecated shims — kept for migration. Will be removed in PR-2 of v0.4.

def read_edn_as_json(path: Path) -> Any:
    warnings.warn(
        "read_edn_as_json is deprecated; use read_edn_file. It will be removed in v0.4 PR-2.",
        DeprecationWarning,
        stacklevel=2,
    )
    return read_edn_file(path)


def write_json_as_edn(path: Path, payload: Any) -> None:
    warnings.warn(
        "write_json_as_edn is deprecated; use write_edn_file. It will be removed in v0.4 PR-2.",
        DeprecationWarning,
        stacklevel=2,
    )
    write_edn_file(path, payload)
