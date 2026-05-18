"""Canonical extract-preview implementation, vendored into each project's
scripts/ dir at scaffold time (mirrors the codegen_axioms.py pattern).

Runs ingest_ledger.ingest() against a JSONL + predicates.edn pair and
prints a per-predicate fact-count summary plus a machine-readable JSON
tail. Exits non-zero when the OPAQUE fraction exceeds the threshold
(default 0.50).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from scripts._edn_reader import Keyword


def _kw(name: str) -> Keyword:
    return Keyword(name)


def _pred_name(p: Any) -> str:
    if isinstance(p, Keyword):
        return p.name
    return str(p).lstrip(":")


def run(claims_jsonl: Path, predicates_edn: Path,
        threshold: float = 0.50, dry_run: bool = False,
        no_fail_gate: bool = False, out: Any = sys.stdout) -> int:
    """Return exit code: 0 on under-threshold, 1 on over-threshold."""
    from scripts.ingest_ledger import ingest
    work_dir = Path(claims_jsonl).resolve().parent.parent / "work"
    work = (Path("/tmp") if dry_run else work_dir) / "_extract_preview_atoms.edn"
    atoms = ingest(claims_jsonl, predicates_edn, work, return_atoms=True)
    if dry_run:
        try:
            print(work.read_text(encoding="utf-8"), file=out)
        except FileNotFoundError:
            pass
        try:
            work.unlink()
        except FileNotFoundError:
            pass

    by_pred: Counter[str] = Counter()
    sample: dict[str, Any] = {}
    opaque = 0
    for a in atoms:
        kind = a.get(_kw("kind"))
        if isinstance(kind, Keyword) and kind.name == "expression":
            pred = a.get(_kw("predicate"))
            pred_name = _pred_name(pred)
            by_pred[pred_name] += 1
            if pred_name not in sample:
                sample[pred_name] = a.get(_kw("value"))
        else:
            name = a.get(_kw("name"))
            if isinstance(name, Keyword) and name.name == "OPAQUE":
                opaque += 1

    total = len(atoms)
    opaque_frac = opaque / max(total, 1)

    print(f"{'Predicate':<32}{'Facts':>8}  Sample value", file=out)
    for p, n in sorted(by_pred.items()):
        print(f"{p:<32}{n:>8}  {sample.get(p, '?')}", file=out)
    print("-" * 60, file=out)
    print(f"{'Total claims':<32}{total:>8}", file=out)
    print(f"{'Atoms (expression)':<32}{sum(by_pred.values()):>8}", file=out)
    print(f"{'OPAQUE / unmatched':<32}{opaque:>8}   ({opaque_frac:.1%})", file=out)
    print(file=out)

    fail = (opaque_frac > threshold)
    if fail and not no_fail_gate:
        print(f"OPAQUE fraction {opaque_frac:.1%} exceeds threshold {threshold:.1%}",
              file=out)
    else:
        print(f"OPAQUE fraction {opaque_frac:.1%} within threshold {threshold:.1%}",
              file=out)

    print("JSON: " + json.dumps({
        "opaque": opaque, "total": total,
        "opaque_fraction": opaque_frac,
        "threshold": threshold,
        "by_predicate": dict(by_pred),
    }), file=out)

    return 1 if fail and not no_fail_gate else 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims", required=True, type=Path)
    ap.add_argument("--predicates", required=True, type=Path)
    ap.add_argument("--threshold", type=float, default=0.50)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-fail-gate", action="store_true")
    args = ap.parse_args(argv)
    return run(args.claims, args.predicates,
               threshold=args.threshold,
               dry_run=args.dry_run,
               no_fail_gate=args.no_fail_gate)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
