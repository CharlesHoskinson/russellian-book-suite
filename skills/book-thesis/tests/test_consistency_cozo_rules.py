"""P3.2 — non-vacuous coverage for the consistency rules the goldens don't fire.

The C0.3 violating golden exercises orphan_paragraph, direct/transitive
contradiction, invariant_violation, and unreachable_supports. Three ported rules
fire on neither golden — declared_conflict, sub_arg_no_chapter, missing_evidence —
so they are pinned here at the rule level (load minimal rows into the store, run
the rule head from rules/consistency.cozo, assert it fires on the bad case and
stays quiet on the good case). Mirrors the M-1 lesson from P2.4: a ported rule that
no test fires is unverified.
"""
from __future__ import annotations

from pathlib import Path

from scripts.sibling_skills import book_knowledge_root, load_book_knowledge_module

RULES = Path(__file__).resolve().parents[1] / "rules" / "consistency.cozo"


def _store():
    cozo_store = load_book_knowledge_module("cozo_store")
    schema = book_knowledge_root() / "assets" / "kg-schema.edn"
    return cozo_store.CozoStore.in_memory(schema_path=schema)


def _head(store, head: str, cols: list[str]) -> set[tuple]:
    program = RULES.read_text(encoding="utf-8")
    col = ", ".join(cols)
    return {tuple(r) for r in store.query(f"{program}\n?[{col}] := {head}[{col}]")}


def test_declared_conflict_is_symmetric():
    store = _store()
    store.load("claim-conflict", [{"id": "a\x1fb", "claim-id": "a", "other-id": "b"}])
    rows = _head(store, "declared_conflict", ["a", "b"])
    # declared_conflict(A,B) holds in both directions for a single declaration.
    assert ("a", "b") in rows and ("b", "a") in rows


def test_sub_arg_no_chapter_fires_only_for_unadvanced():
    store = _store()
    store.load("sub-argument", [
        {"id": "s-bare", "parent": "thesis"},
        {"id": "s-advanced", "parent": "thesis"},
    ])
    store.load("sub-arg-chapter", [
        {"id": "s-advanced\x1fch-1", "sub-arg-id": "s-advanced", "chapter": "ch-1"},
    ])
    rows = _head(store, "sub_arg_no_chapter", ["n"])
    assert ("s-bare",) in rows
    assert ("s-advanced",) not in rows


def test_missing_evidence_fires_only_for_unmet_slot():
    store = _store()
    store.load("sub-argument", [{"id": "s1", "parent": "thesis"}])
    store.load("sub-arg-evidence", [
        {"id": "s1\x1fgeography", "sub-arg-id": "s1", "evidence": "geography"},
        {"id": "s1\x1feconomy", "sub-arg-id": "s1", "evidence": "economy"},
    ])
    # a claim whose subject MEETS the economy slot, but nothing meets geography.
    store.load("claim-fact", [{"id": "c1", "subject": "economy"}])
    rows = _head(store, "missing_evidence", ["n", "e"])
    assert ("s1", "geography") in rows
    assert ("s1", "economy") not in rows
