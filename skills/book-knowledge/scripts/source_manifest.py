"""Source manifest hashing, doc_id computation, schema validation."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import jsonschema

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SCHEMA = json.loads((ASSETS / "source-manifest.schema.json").read_text(encoding="utf-8"))


class ManifestValidationError(Exception):
    pass


def compute_doc_id(filename: str) -> str:
    stem = Path(filename).stem
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", stem).strip("-").lower()
    cleaned = re.sub(r"-+", "-", cleaned)
    return cleaned


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_manifest(record: dict) -> None:
    try:
        jsonschema.validate(record, SCHEMA)
    except jsonschema.ValidationError as e:
        raise ManifestValidationError(str(e)) from e


def write_manifest(path: Path, record: dict) -> None:
    validate_manifest(record)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")


def load_manifest(path: Path) -> dict:
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_manifest(record)
    return record
