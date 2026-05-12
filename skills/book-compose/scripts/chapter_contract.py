"""Validate and scaffold chapter contracts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import jsonschema
import yaml

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
    if cc_path.exists():
        latest: dict[str, dict] = {}
        for line in cc_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            cc = json.loads(line)
            latest[cc["id"]] = cc
        for cc in latest.values():
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
