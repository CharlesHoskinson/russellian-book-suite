"""REQ-EDN-052, REQ-EDN-053: booklogic-schema.edn lists predicate signatures
and ingest_ledger validates predicates.edn against it."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = PROJECT_ROOT / "rules" / "booklogic-schema.edn"


def test_schema_file_exists():
    assert SCHEMA.exists(), f"booklogic-schema.edn must exist at {SCHEMA}"


def test_schema_lists_four_predicates_with_return_real():
    text = SCHEMA.read_text(encoding="utf-8")
    for pred in ("osmotic-pressure-pa", "vant-hoff-i", "molarity", "temperature-k"):
        assert pred in text, f"predicate {pred!r} not in schema"
    assert ":return :real" in text
    assert ":arg-sorts [:solution]" in text or ":arg-sorts (:solution)" in text


def test_schema_emits_vector_set_return_shapes(tmp_path):
    """REQ-DSL-055: a multi-valued return shape ([:vector T] / [:set T]) in
    a hand-rolled booklogic-schema.edn round-trips through the EDN reader
    used by ingest_ledger, preserving the container head + inner sort."""
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts._edn_reader import read_edn, Keyword

    text = (
        "{:version 1 "
        " :sorts [:solution :chapter] "
        " :predicates {"
        "   :solutes           {:arg-sorts [:solution] :return [:vector :real]} "
        "   :upstream-chapters {:arg-sorts [:chapter]  :return [:set :chapter]}}}"
    )
    parsed = read_edn(text)
    preds  = parsed[Keyword("predicates")]
    solutes = preds[Keyword("solutes")]
    assert solutes[Keyword("return")][0] == Keyword("vector")
    assert solutes[Keyword("return")][1] == Keyword("real")
    upstream = preds[Keyword("upstream-chapters")]
    assert upstream[Keyword("return")][0] == Keyword("set")
    assert upstream[Keyword("return")][1] == Keyword("chapter")


def test_unknown_predicate_rejects_ingest(tmp_path):
    """REQ-EDN-053: ingest fails fast if predicates.edn references a name
    not in the schema."""
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.ingest_ledger import ingest as _ingest

    # Sibling schema referencing only :molarity
    schema_file = tmp_path / "booklogic-schema.edn"
    schema_file.write_text(
        '{:version 1 :sorts [:solution] '
        ':predicates {:molarity {:arg-sorts [:solution] :return :real}}}',
        encoding="utf-8",
    )
    # Predicates.edn with an unknown predicate
    preds_file = tmp_path / "predicates.edn"
    preds_file.write_text(
        '{:version 1 :predicates {:Osmotic-Pressure '
        '{:patterns ["x"], :predicate :Osmotic-Pressure, :subject :s, '
        ':value-kind :real, :word-to-int {}}}}',
        encoding="utf-8",
    )
    out = tmp_path / "claims.edn"
    ledger = PROJECT_ROOT / "fixtures" / "claims_clean.jsonl"

    # ingest should exit(1) via sys.exit on unknown predicate
    with pytest.raises(SystemExit) as exc_info:
        _ingest(ledger, preds_file, out)
    assert exc_info.value.code == 1
