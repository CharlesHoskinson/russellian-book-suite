"""REQ-CORPUS-041: at-least-1000 claims, 8+ predicates fire."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.ingest_ledger import compute_atoms
from scripts._edn_reader import Keyword


def _by_predicate_counts(atoms) -> dict[str, int]:
    counts: dict[str, int] = {}
    for a in atoms:
        kind = a.get(Keyword("kind"))
        if isinstance(kind, Keyword) and kind.name == "expression":
            pred = a.get(Keyword("predicate"))
            name = pred.name if isinstance(pred, Keyword) else str(pred).lstrip(":")
            counts[name] = counts.get(name, 0) + 1
    return counts


def test_at_least_1000_claims_eight_predicates(project_root: Path) -> None:
    claims_path = project_root / "fixtures" / "claims_clean.jsonl"
    predicates_path = project_root / "rules" / "predicates.edn"

    n_claims = 0
    with claims_path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                json.loads(line)
                n_claims += 1
    assert n_claims >= 1000, f"only {n_claims} claims; need >= 1000"

    atoms = compute_atoms(claims_path, predicates_path)
    by_pred = _by_predicate_counts(atoms)
    assert len(by_pred) >= 8, (
        f"only {len(by_pred)} predicates fire: {sorted(by_pred)}; need >= 8"
    )
