"""Cross-check claim source spans against raw/ files; promote proposed -> verified."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

from .ledger import read_claims, transition_status, LedgerError
from .source_manifest import load_manifest
from .workspace import WorkspaceLayout


@dataclass(frozen=True)
class VerificationResult:
    claim_id: str
    ok: bool
    new_status: str
    reason: str = ""


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _load_source_text(layout: WorkspaceLayout, doc_id: str) -> str:
    manifest_path = layout.manifests / f"{doc_id}.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"no manifest for doc_id={doc_id}")
    manifest = load_manifest(manifest_path)
    if manifest["source_kind"] == "markdown":
        path = layout.raw_markdown / manifest["doc_name"]
        return path.read_text(encoding="utf-8")
    if manifest["source_kind"] == "pdf":
        path = layout.raw_pdf / manifest["doc_name"]
        with pdfplumber.open(str(path)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    raise ValueError(f"unknown source_kind={manifest['source_kind']}")


def _find_claim(layout: WorkspaceLayout, claim_id: str) -> dict | None:
    found: dict | None = None
    for record in read_claims(layout):
        if record["claim_id"] == claim_id:
            found = record
    return found


def verify_claim(layout: WorkspaceLayout, claim_id: str) -> VerificationResult:
    claim = _find_claim(layout, claim_id)
    if claim is None:
        raise LedgerError(f"unknown claim_id={claim_id}")

    for span in claim["source_spans"]:
        source_text = _load_source_text(layout, span["doc_id"])
        if _normalize(span["locator_text"]) not in _normalize(source_text):
            return VerificationResult(
                claim_id=claim_id, ok=False, new_status=claim["status"],
                reason=f"locator_text not found in {span['doc_id']}",
            )

    if claim["status"] == "proposed":
        transition_status(layout, claim_id, "verified", note="locator-text confirmed")
    return VerificationResult(claim_id=claim_id, ok=True, new_status="verified")
