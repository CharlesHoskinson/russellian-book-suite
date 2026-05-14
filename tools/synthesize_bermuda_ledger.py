#!/usr/bin/env python
"""One-shot: synthesize a book-knowledge ledger for bermuda-manual from its thesis.

The bermuda example currently uses book-thesis but has no book-knowledge ledger.
This tool builds one by translating thesis sub-arguments and invariants into
ledger records:

  - Each sub_argument becomes a `claim_type: design_decision` claim whose
    supports_chapters mirrors its advanced_by_chapters.
  - Each invariant becomes a `claim_type: fact` claim (cross-cutting, no
    chapter binding).
  - Source span points to the thesis YAML (doc_id "thesis").

The result is a small but real book-knowledge workspace that Bundle C can
exercise end-to-end.

Usage:
    python tools/synthesize_bermuda_ledger.py examples/bermuda-manual
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _claim_id(year: int, n: int) -> str:
    return f"clm-{year}-{n:06d}"


def synthesize(workspace_root: Path) -> int:
    thesis_path = workspace_root / "thesis" / "bermuda-manual.yaml"
    if not thesis_path.exists():
        print(f"no thesis at {thesis_path}", file=sys.stderr)
        return 0
    data = yaml.safe_load(thesis_path.read_text(encoding="utf-8"))

    workspace_root.mkdir(parents=True, exist_ok=True)
    (workspace_root / "claims").mkdir(parents=True, exist_ok=True)
    (workspace_root / "raw" / "manifests").mkdir(parents=True, exist_ok=True)
    (workspace_root / "wiki").mkdir(parents=True, exist_ok=True)
    (workspace_root / "graph").mkdir(parents=True, exist_ok=True)

    ledger = workspace_root / "claims" / "ledger.jsonl"
    if ledger.exists() and ledger.read_text(encoding="utf-8").strip():
        print(f"ledger already populated at {ledger}; refusing to clobber", file=sys.stderr)
        return 0

    year = datetime.now(timezone.utc).year
    now = _now_iso()
    records: list[dict] = []
    n = 0

    # 1. Thesis itself as a top-level design_decision.
    thesis = data["thesis"]
    n += 1
    records.append({
        "claim_id": _claim_id(year, n),
        "canonical_text": thesis["statement"].strip(),
        "status": "verified",
        "claim_type": "design_decision",
        "confidence": 0.9,
        "source_spans": [{"doc_id": "thesis", "locator_text": "thesis:statement"}],
        "supports_chapters": [],  # thesis is cross-cutting
        "created_at": now,
        "generated_by_run": "synthesize-bermuda-2026-05-12",
        "review_notes": "Top-level book thesis; translated from thesis/bermuda-manual.yaml.",
    })

    # 2. Each sub_argument becomes a chapter-bound design_decision.
    for sub in data.get("sub_arguments", []):
        n += 1
        records.append({
            "claim_id": _claim_id(year, n),
            "canonical_text": sub["statement"].strip(),
            "status": "verified",
            "claim_type": "design_decision",
            "confidence": 0.85,
            "source_spans": [{"doc_id": "thesis",
                              "locator_text": f"sub_arguments/{sub['id']}"}],
            "supports_chapters": list(sub.get("advanced_by_chapters", [])),
            "created_at": now,
            "generated_by_run": "synthesize-bermuda-2026-05-12",
            "review_notes": f"Sub-argument {sub['id']!r} from thesis tree.",
        })

    # 3. Each invariant becomes a canonical fact (cross-cutting; no chapter binding).
    for inv in data.get("invariants", []):
        n += 1
        records.append({
            "claim_id": _claim_id(year, n),
            "canonical_text": inv["rule"].strip(),
            "status": "verified",
            "claim_type": "fact",
            "confidence": 0.95,
            "source_spans": [{"doc_id": "thesis",
                              "locator_text": f"invariants/{inv['id']}"}],
            "supports_chapters": [],
            "created_at": now,
            "generated_by_run": "synthesize-bermuda-2026-05-12",
            "review_notes": f"Canonical invariant {inv['id']!r}; cross-cutting fact.",
        })

    # Write the ledger (append-only semantics: write each record on its own line).
    with ledger.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, sort_keys=True) + "\n")

    # Source manifest for the thesis "document" — schema-valid per source-manifest.schema.json.
    manifest = workspace_root / "raw" / "manifests" / "thesis.json"
    if not manifest.exists():
        sha256 = hashlib.sha256(thesis_path.read_bytes()).hexdigest() if thesis_path.exists() else "0" * 64
        manifest.write_text(json.dumps({
            "doc_name": "bermuda-manual thesis",
            "doc_id": "thesis",
            "source_kind": "markdown",
            "sha256": sha256,
            "node_count": n,
            "ingested_at": now,
            "trust": 1.0,
        }, sort_keys=True, indent=2), encoding="utf-8")

    return len(records)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: synthesize_bermuda_ledger.py <workspace>", file=sys.stderr)
        return 2
    ws = Path(argv[1])
    n = synthesize(ws)
    print(f"wrote {n} claims to {ws}/claims/ledger.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
