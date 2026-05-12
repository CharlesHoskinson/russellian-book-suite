"""Counter-claim records — append-only parallel ledger keyed by cc-XXXX-XXXXXX."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from .workspace import WorkspaceLayout

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SCHEMA = json.loads((ASSETS / "counter-claim.schema.json").read_text(encoding="utf-8"))


class CounterClaimError(Exception):
    pass


def validate_counter_claim(record: dict) -> None:
    try:
        jsonschema.validate(record, SCHEMA)
    except jsonschema.ValidationError as e:
        raise CounterClaimError(str(e)) from e


def _path(workspace_root: Path) -> Path:
    return WorkspaceLayout(workspace_root).root / "claims" / "counter-claims.jsonl"


def append_counter_claim(workspace_root: Path, record: dict) -> None:
    validate_counter_claim(record)
    path = _path(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def read_counter_claims(workspace_root: Path) -> list[dict]:
    path = _path(workspace_root)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def next_counter_claim_id(workspace_root: Path) -> str:
    """Generate cc-YYYY-NNNNNN; NN is hex random for collision tolerance."""
    import secrets
    from datetime import datetime, timezone
    year = datetime.now(timezone.utc).year
    return f"cc-{year}-{secrets.token_hex(3)}"
