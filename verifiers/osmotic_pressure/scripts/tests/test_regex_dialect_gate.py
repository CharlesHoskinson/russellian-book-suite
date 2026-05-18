"""Phase E tests: REQ-INGEST-050..052.

Strict Python regex dialect at the ingest boundary. JS-style named
groups `(?<v>...)` must be rejected at ingest time with a hard
IngestRegexDialectError, rather than silently rewritten. The
extract-preview OPAQUE-fraction gate still fires on dialect-correct
but non-matching patterns.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ingest_ledger import (
    IngestRegexDialectError,
    compute_atoms,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _write_predicates(tmp_path: Path, patterns: list[str]) -> Path:
    """Write a minimal predicates.edn with the given patterns under :probe."""
    pats = " ".join(f'"{p}"' for p in patterns)
    preds = tmp_path / "predicates.edn"
    preds.write_text(
        "{:version 1, :predicates {:probe {:patterns [" + pats + "], "
        ":predicate :probe, :subject :s, :value-kind :real, :word-to-int {}}}}",
        encoding="utf-8",
    )
    return preds


def _write_ledger(tmp_path: Path, text: str) -> Path:
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        '{"claim_id":"c-001","status":"verified","canonical_text":"'
        + text + '","claim_type":"fact"}\n',
        encoding="utf-8",
    )
    return ledger


def test_js_style_named_group_raises(tmp_path):
    """REQ-INGEST-050, 051: JS-style (?<v>) named groups must raise
    IngestRegexDialectError with a diagnostic that names the offending
    pattern, rather than being silently rewritten."""
    preds = _write_predicates(tmp_path, [r"count\s*(?<v>[0-9]+)"])
    ledger = _write_ledger(tmp_path, "count 7")
    with pytest.raises(IngestRegexDialectError) as exc_info:
        compute_atoms(ledger, preds)
    msg = str(exc_info.value)
    assert "(?<" in msg, (
        f"diagnostic must quote the offending JS-style construct; got: {msg!r}"
    )


def test_dialect_correct_but_nonmatching_still_triggers_opaque_gate(tmp_path):
    """REQ-INGEST-052: a Python-dialect-correct but non-matching pattern
    still produces OPAQUE atoms, so the extract-preview gate fires on
    pattern-author bugs that aren't dialect errors. Removing the silent
    JS converter must not weaken the second-layer gate."""
    preds = _write_predicates(tmp_path, [r"zzzNEVERMATCH\s*(?P<v>[0-9]+)"])
    ledger = _write_ledger(tmp_path, "count 7")
    atoms = compute_atoms(ledger, preds)
    assert len(atoms) == 1
    from scripts._edn_reader import Keyword
    atom = atoms[0]
    assert atom.get(Keyword("name")) == Keyword("OPAQUE"), (
        f"non-matching dialect-correct pattern must yield OPAQUE; got: {atom!r}"
    )
