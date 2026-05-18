"""Validate and scaffold chapter contracts."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import jsonschema
import yaml

from .sibling_skills import SiblingNotFoundError, load_book_knowledge_module

_log = logging.getLogger(__name__)

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SCHEMA = json.loads((ASSETS / "chapter-contract.schema.json").read_text(encoding="utf-8"))
TEMPLATE = (ASSETS / "chapter-contract.template.yaml").read_text(encoding="utf-8")


class ContractValidationError(Exception):
    pass


def validate_contract(record: dict) -> None:
    try:
        jsonschema.validate(record, SCHEMA)
    except jsonschema.ValidationError as e:
        raise ContractValidationError(str(e)) from e


def _read_counter_claims_local(path: Path) -> list[dict]:
    """Fallback counter-claims reader used when the book-knowledge sibling is not installed.

    Returns last-write-wins per id; skips blank and malformed lines.
    """
    if not path.exists():
        return []
    latest: dict[str, dict] = {}
    for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            latest[rec["id"]] = rec
        except (json.JSONDecodeError, KeyError) as e:
            _log.warning("skipping malformed JSONL line %d in %s: %s", i, path, e)
    return list(latest.values())


def load_contract(path: Path) -> dict:
    record = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    validate_contract(record)
    return record


def load_brief(workspace_root: Path, path: Path) -> dict:
    """Load a contract and attach must_address from open counter-claims.

    must_address entries match counter-claims whose target_claim_id is in the
    contract's `claims` list and whose status is "open".  Returns the contract
    dict augmented with a `must_address` key (list[dict], may be empty).
    """
    brief = load_contract(path)
    chapter_claims = set(brief.get("claims") or [])
    must_address: list[dict] = []
    cc_path = Path(workspace_root) / "claims" / "counter-claims.jsonl"
    try:
        io = load_book_knowledge_module("io_utils")
        raw_ccs = list(io.latest_per(io.read_jsonl(cc_path), "id").values())
    except SiblingNotFoundError:
        raw_ccs = _read_counter_claims_local(cc_path)
    for cc in raw_ccs:
        if cc.get("status") != "open":
            continue
        if cc.get("target_claim_id") in chapter_claims:
            must_address.append({
                "counter_claim_id": cc["id"],
                "text": cc["text"],
                "target_claim_id": cc["target_claim_id"],
            })
    brief["must_address"] = must_address
    return brief


def scaffold_contract(chapter_id: str, out_path: Path) -> None:
    out_path = Path(out_path)
    if out_path.exists():
        raise FileExistsError(f"will not overwrite {out_path}")
    text = TEMPLATE.replace("chapter_id: ch-01", f"chapter_id: {chapter_id}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
