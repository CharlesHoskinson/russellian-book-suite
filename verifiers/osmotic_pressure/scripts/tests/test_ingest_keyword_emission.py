"""REQ-EDN-049: ingest_ledger emits :predicate and :subject as Edn Keywords,
not string-with-colon-prefix."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts._edn_reader import Keyword
from scripts.ingest_ledger import ingest


def test_predicate_and_subject_are_keywords(tmp_path):
    """The atom-emitter must produce Keyword objects for :predicate and
    :subject, not Python strs with `:` prefix. The Rust verifier no
    longer carries the Edn::Str fallback for these fields."""
    out = tmp_path / "claims.edn"
    n = ingest(
        PROJECT_ROOT / "fixtures" / "claims_clean.jsonl",
        PROJECT_ROOT / "rules" / "predicates.edn",
        out,
    )
    text = out.read_text(encoding="utf-8")
    # A Keyword emitted by _edn_writer renders as `:foo`, NOT as the
    # double-quoted string `":foo"`. The presence of `:predicate ":` is
    # the smoking gun for the old stringly-typed format.
    assert ':predicate ":' not in text, (
        f"ingest emitted stringly-typed :predicate; got:\n{text[:500]}"
    )
    assert ':subject ":' not in text, (
        f"ingest emitted stringly-typed :subject; got:\n{text[:500]}"
    )
    # And at least one of the clean-fixture predicates should appear as a
    # keyword token.
    found = any(
        f":predicate :{p}" in text
        for p in ("osmotic-pressure-pa", "molarity", "vant-hoff-i", "temperature-k")
    )
    assert found, (
        f"no clean-fixture predicate found as :predicate :keyword in output:\n{text[:500]}"
    )
    assert n > 0
