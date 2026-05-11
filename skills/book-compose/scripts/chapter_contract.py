"""Validate and scaffold chapter contracts."""
from __future__ import annotations

import json
from pathlib import Path

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


def scaffold_contract(chapter_id: str, out_path: Path) -> None:
    out_path = Path(out_path)
    if out_path.exists():
        raise FileExistsError(f"will not overwrite {out_path}")
    text = TEMPLATE.replace("chapter_id: ch-01", f"chapter_id: {chapter_id}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
