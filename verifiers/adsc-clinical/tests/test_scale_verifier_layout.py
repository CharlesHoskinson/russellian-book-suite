"""REQ-CORPUS-040: standard project layout for the fourth verifier."""
from __future__ import annotations

from pathlib import Path


def test_standard_project_files_present(project_root: Path) -> None:
    """The verifier ships the standard scaffold tree."""
    expected = [
        "Makefile",
        "README.md",
        "SKILL.md",
        "package.json",
        "deps.edn",
        "nbb.edn",
        "shadow-cljs.edn",
        "rules/booklogic/sorts.edn",
        "rules/booklogic/predicates.edn",
        "rules/booklogic/lifts.edn",
        "rules/booklogic/constraints.edn",
        "rules/predicates.edn",
        "fixtures/claims_clean.jsonl",
        "scripts/ingest_ledger.py",
        "scripts/extract_preview.py",
        "rust-verifier/Cargo.toml",
        "cljs-orchestrator/src/main/adsc_clinical/core.cljs",
    ]
    missing = [p for p in expected if not (project_root / p).exists()]
    assert not missing, f"missing standard files: {missing}"
