"""Counter-claim records — append-only parallel ledger keyed by cc-XXXX-XXXXXX."""
from __future__ import annotations

import argparse
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

from .io_utils import latest_per, read_jsonl
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
    return read_jsonl(_path(workspace_root))


def next_counter_claim_id(workspace_root: Path,
                          reserved: set[str] | None = None) -> str:
    """Generate a fresh cc-YYYY-XXXXXX id that does not collide.

    Checks the generated id against ids already in the counter-claim ledger and
    against `reserved` (ids minted earlier in the same batch but not yet
    written), regenerating on collision. Without this, two counter-claims could
    share an id and be conflated under latest-per-id dedup in propagation.
    """
    year = datetime.now(timezone.utc).year
    taken = {r["id"] for r in read_counter_claims(workspace_root) if "id" in r}
    if reserved:
        taken |= reserved
    while True:
        candidate = f"cc-{year}-{secrets.token_hex(3)}"
        if candidate not in taken:
            return candidate


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.counter_claims",
        description="List counter-claims in a workspace (latest revision per id).",
        usage="python -m scripts.counter_claims <workspace> [--status STATUS] [--target CLAIM_ID]",
    )
    parser.add_argument("workspace", type=Path, help="Workspace root.")
    parser.add_argument("--status", help="Filter by status (e.g. open, addressed).")
    parser.add_argument("--target", help="Filter by target_claim_id.")
    args = parser.parse_args(argv)
    records = list(latest_per(read_counter_claims(args.workspace.resolve()), "id").values())
    if args.status:
        records = [r for r in records if r.get("status") == args.status]
    if args.target:
        records = [r for r in records if r.get("target_claim_id") == args.target]
    records.sort(key=lambda r: r.get("id", ""))
    for r in records:
        print(f"{r['id']}\t{r.get('status', '?')}\t{r.get('target_claim_id', '?')}\t{r.get('text', '')}")
    print(f"total: {len(records)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
