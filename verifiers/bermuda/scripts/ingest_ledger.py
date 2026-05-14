"""Bermuda-specific ledger ingester.

Reads examples/bermuda-manual/claims/ledger.jsonl, applies the predicate
map in rules/predicates.edn to fact-class claims, and emits typed atoms
to work/claims.edn. design_decision claims are emitted as :context atoms.

Generated initially by neurosym-forge --book-knowledge-bridge, then
specialized for the Bermuda predicate set.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def read_ledger(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def latest_per_id(rows: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in rows:
        cid = r.get("claim_id") or r.get("id")
        if cid:
            out[cid] = r
    return out


def _is_verified(c: dict) -> bool:
    return c.get("status") == "verified" or c.get("tbf:status") == "verified"


def _apply_predicates(text: str, predicates: dict[str, dict]) -> tuple[str, Any, str] | None:
    """Match text against the predicate map. Returns (predicate, value, subject) or None."""
    for _name, spec in predicates.items():
        for pat in spec.get("patterns", []):
            m = re.search(pat, text, flags=re.IGNORECASE | re.DOTALL)
            if not m:
                continue
            value_kind = spec.get("value_kind")
            if value_kind == "bool":
                value = spec.get("value", True)
            elif value_kind == "int":
                raw = m.group("n") if "n" in m.groupdict() else m.group(1)
                value = spec.get("word_to_int", {}).get(raw.lower(), None)
                if value is None:
                    try:
                        value = int(raw)
                    except ValueError:
                        continue
            elif value_kind == "string":
                value = m.group("binomial").strip()
            elif value_kind == "entity":
                value = m.group("island").replace(".", "").replace(" ", "_")
            else:
                continue
            return spec["predicate"], value, spec["subject"]
    return None


def _claim_to_atom(claim: dict, predicates: dict[str, dict]) -> dict:
    text = claim.get("canonical_text", "")
    base: dict[str, Any] = {
        "id": claim.get("claim_id", "?"),
        "doc": text[:200],
        "source_spans": claim.get("source_spans", []),
        "supports_chapters": claim.get("supports_chapters", []),
        "confidence": claim.get("confidence", 0.0),
    }
    if claim.get("claim_type") == "design_decision":
        base.update({"kind": "symbol", "sort": ":formula",
                     "name": ":CONTEXT", "context": True})
        return base
    match = _apply_predicates(text, predicates)
    if match is None:
        base.update({"kind": "symbol", "sort": ":formula", "name": ":OPAQUE"})
        return base
    predicate, value, subject = match
    base.update({"kind": "expression", "sort": ":formula",
                 "predicate": predicate, "subject": subject, "value": value,
                 "context": False})
    return base


def ingest(ledger_path: Path, predicates_path: Path, out_path: Path) -> int:
    rows = read_ledger(ledger_path)
    latest = latest_per_id(rows)
    verified = [c for c in latest.values() if _is_verified(c)]
    predicates = json.loads(predicates_path.read_text(encoding="utf-8")).get(
        "predicates", {}
    )
    atoms = [_claim_to_atom(c, predicates) for c in verified]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"version": 1, "atoms": atoms}, indent=2, sort_keys=True),
        encoding="utf-8", newline="\n",
    )
    return len(atoms)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--predicates", required=True)
    ap.add_argument("--out", default="work/claims.edn")
    args = ap.parse_args(argv)
    n = ingest(Path(args.ledger), Path(args.predicates), Path(args.out))
    print(f"ingested {n} verified atoms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
