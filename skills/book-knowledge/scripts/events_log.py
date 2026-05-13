"""Append-only state-transition log for the claim ledger."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from .io_utils import read_jsonl
from .workspace import WorkspaceLayout

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SCHEMA = json.loads((ASSETS / "events.schema.json").read_text(encoding="utf-8"))


class EventError(Exception):
    pass


def _path(workspace_root: Path) -> Path:
    return WorkspaceLayout(workspace_root).root / "claims" / "events.jsonl"


def append_event(workspace_root: Path, event: dict) -> None:
    try:
        jsonschema.validate(event, SCHEMA)
    except jsonschema.ValidationError as e:
        raise EventError(str(e)) from e
    p = _path(workspace_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")


def read_events(workspace_root: Path) -> list[dict]:
    return read_jsonl(_path(workspace_root))
