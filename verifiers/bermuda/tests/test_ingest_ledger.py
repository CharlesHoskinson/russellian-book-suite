from __future__ import annotations

import json
from pathlib import Path


from scripts._edn_reader import Keyword
from scripts._io import read_edn_file
from scripts.ingest_ledger import ingest, read_ledger, latest_per_id

_KW_ATOMS = Keyword("atoms")
_KW_PREDICATE = Keyword("predicate")
_KW_VALUE = Keyword("value")
_KW_ID = Keyword("id")
_KW_CONTEXT = Keyword("context")
_KW_KIND = Keyword("kind")


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
    payload = read_edn_file(tmp_work / "claims.edn")
    atoms = payload[_KW_ATOMS]
    assert len(atoms) == 3
    # Parish-count fact should match the predicate map → :parishes-count atom
    parish_atoms = [a for a in atoms if a.get(_KW_PREDICATE) == Keyword("parishes-count")]
    assert len(parish_atoms) == 1
    assert parish_atoms[0][_KW_VALUE] == 9
    assert parish_atoms[0][_KW_ID] == "clm-2026-000001"


def test_design_decision_emitted_as_context(fixtures_dir: Path, project_root: Path,
                                            tmp_work: Path) -> None:
    ingest(fixtures_dir / "ledger_clean.jsonl",
           project_root / "rules" / "predicates.edn",
           tmp_work / "claims.edn")
    payload = read_edn_file(tmp_work / "claims.edn")
    cedar = [a for a in payload[_KW_ATOMS] if a[_KW_ID] == "clm-2026-000003"][0]
    assert cedar[_KW_CONTEXT] is True


def test_unverified_claims_skipped(tmp_path: Path, project_root: Path, tmp_work: Path) -> None:
    bad = tmp_path / "proposed.jsonl"
    bad.write_text(json.dumps({
        "claim_id": "clm-2026-000999", "claim_type": "fact",
        "canonical_text": "x", "status": "proposed", "confidence": 0.5,
    }) + "\n", encoding="utf-8")
    n = ingest(bad, project_root / "rules" / "predicates.edn", tmp_work / "claims.edn")
    assert n == 0
