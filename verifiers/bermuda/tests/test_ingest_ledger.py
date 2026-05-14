from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ingest_ledger import ingest, read_ledger, latest_per_id


def test_reads_jsonl(fixtures_dir: Path) -> None:
    rows = read_ledger(fixtures_dir / "ledger_clean.jsonl")
    assert len(rows) == 3


def test_latest_per_id_deduplicates(fixtures_dir: Path) -> None:
    rows = read_ledger(fixtures_dir / "ledger_clean.jsonl") + read_ledger(
        fixtures_dir / "ledger_clean.jsonl"
    )
    latest = latest_per_id(rows)
    assert len(latest) == 3


def test_emits_atoms_for_verified_facts(fixtures_dir: Path, project_root: Path,
                                        tmp_work: Path) -> None:
    n = ingest(
        ledger_path=fixtures_dir / "ledger_clean.jsonl",
        predicates_path=project_root / "rules" / "predicates.edn",
        out_path=tmp_work / "claims.edn",
    )
    assert n == 3
    payload = json.loads((tmp_work / "claims.edn").read_text(encoding="utf-8"))
    atoms = payload["atoms"]
    assert len(atoms) == 3
    # Parish-count fact should match the predicate map → :parishes-count atom
    parish_atoms = [a for a in atoms if a.get("predicate") == ":parishes-count"]
    assert len(parish_atoms) == 1
    assert parish_atoms[0]["value"] == 9
    assert parish_atoms[0]["id"] == "clm-2026-000001"


def test_design_decision_emitted_as_context(fixtures_dir: Path, project_root: Path,
                                            tmp_work: Path) -> None:
    ingest(fixtures_dir / "ledger_clean.jsonl",
           project_root / "rules" / "predicates.edn",
           tmp_work / "claims.edn")
    payload = json.loads((tmp_work / "claims.edn").read_text(encoding="utf-8"))
    cedar = [a for a in payload["atoms"] if a["id"] == "clm-2026-000003"][0]
    assert cedar["context"] is True


def test_unverified_claims_skipped(tmp_path: Path, project_root: Path, tmp_work: Path) -> None:
    bad = tmp_path / "proposed.jsonl"
    bad.write_text(json.dumps({
        "claim_id": "clm-2026-000999", "claim_type": "fact",
        "canonical_text": "x", "status": "proposed", "confidence": 0.5,
    }) + "\n", encoding="utf-8")
    n = ingest(bad, project_root / "rules" / "predicates.edn", tmp_work / "claims.edn")
    assert n == 0
