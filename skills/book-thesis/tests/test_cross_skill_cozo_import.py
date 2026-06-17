"""P3.0 — book-thesis can import book-knowledge's Cozo modules (option b).

P3 retires pyDatalog by projecting the thesis spine into book-knowledge's Cozo
store (P3.1, via a NEW thesis projector) and running the EDN->Cozo consistency
pass (P3.2). That needs book-thesis to import book-knowledge's `cozo_store` (the
store seam) and `booklogic_kg` (the EDN->CozoScript compiler) — NOT the
claim-side `project_ledger_cozo`, whose transitive deps (jsonschema, pdfplumber,
…) would drag book-knowledge's full ledger stack into book-thesis's venv. Both
skills define a top-level `scripts` package, so a plain `import scripts.cozo_store`
would collide; we load book-knowledge's modules under the `_book_knowledge_scripts`
alias (the same mechanism book-compose uses), resolving book-knowledge RELATIVE TO
book-thesis's own location so the copy running alongside this one is used — never a
stale cross-tree `~/.claude` copy that lacks the P2 Cozo work.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sibling_skills import book_knowledge_root, load_book_knowledge_module

# book-thesis/tests/ -> book-thesis -> skills -> skills/book-knowledge
REPO_BK = Path(__file__).resolve().parents[2] / "book-knowledge"


def test_resolves_repo_book_knowledge_with_p2_assets():
    """The resolved root is a real book-knowledge skill carrying the P2-current
    Cozo assets (incl. P2.4's status-present.edn) — i.e. NOT a stale copy."""
    root = book_knowledge_root()
    assert (root / "SKILL.md").is_file()
    assert (root / "scripts" / "cozo_store.py").is_file()
    assert (root / "assets" / "kg-schema.edn").is_file()
    # P2.4 artifact: present only on the up-to-date repo copy.
    assert (root / "assets" / "kg-constraints" / "status-present.edn").is_file()
    assert root == REPO_BK


def test_loads_and_runs_cozo_store_and_compiler():
    """Loading cozo_store + booklogic_kg under the alias works end to end —
    including booklogic_kg's `from .cozo_store import to_snake` relative import,
    which only resolves when the module is loaded inside the alias package."""
    cozo_store = load_book_knowledge_module("cozo_store")
    booklogic = load_book_knowledge_module("booklogic_kg")
    schema = book_knowledge_root() / "assets" / "kg-schema.edn"

    store = cozo_store.CozoStore.in_memory(schema_path=schema)
    store.load("claim", [
        {"id": "c1", "status": "verified", "confidence": 0.9, "canonical-text": "x"},
    ])
    edn = (book_knowledge_root() / "assets" / "kg-constraints"
           / "status-present.edn").read_text(encoding="utf-8")
    script = booklogic.compile_constraint(edn, schema)
    rows = store.query(script)
    assert rows == []  # c1 HAS a status -> no status-present violation


def test_query_edn_through_alias_loaded_store():
    """`CozoStore.query_edn` lazily does `from .booklogic_kg import compile_query`
    from inside the alias-loaded cozo_store — exercise that path (P3.1 will use
    query_edn), not just the raw `query` path the other tests cover."""
    cozo_store = load_book_knowledge_module("cozo_store")
    schema = book_knowledge_root() / "assets" / "kg-schema.edn"
    store = cozo_store.CozoStore.in_memory(schema_path=schema)
    store.load("claim", [
        {"id": "v1", "status": "verified", "confidence": 0.9, "canonical-text": "a"},
        {"id": "p1", "status": "proposed", "confidence": 0.5, "canonical-text": "b"},
    ])
    rows = store.query_edn(
        "(defquery :verified-claims :find [?id] "
        ":where [[?c :claim/id ?id] [?c :claim/status \"verified\"]])"
    )
    assert [r[0] for r in rows] == ["v1"]


def test_compiled_constraint_fires_on_violating_row():
    """End-to-end through the alias: a status-less claim is a violation, proving
    the loaded compiler + store agree across the skill boundary."""
    cozo_store = load_book_knowledge_module("cozo_store")
    booklogic = load_book_knowledge_module("booklogic_kg")
    schema = book_knowledge_root() / "assets" / "kg-schema.edn"

    store = cozo_store.CozoStore.in_memory(schema_path=schema)
    store.load("claim", [{"id": "c-no-status", "confidence": 0.5,
                          "canonical-text": "no status"}])
    edn = (book_knowledge_root() / "assets" / "kg-constraints"
           / "status-present.edn").read_text(encoding="utf-8")
    rows = store.query(booklogic.compile_constraint(edn, schema))
    assert [r[0] for r in rows] == ["c-no-status"]


def test_alias_collision_raises_instead_of_serving_wrong_root(monkeypatch):
    """If the process-global _book_knowledge_scripts alias was already registered
    for a DIFFERENT book-knowledge (e.g. book-compose's installed-first loader ran
    in the same interpreter), the loader must fail loud rather than silently serve
    the wrong (stale) copy (audit IMPORTANT)."""
    import sys as _sys
    import types as _types

    from scripts import sibling_skills as ss

    bogus = _types.ModuleType(ss._BK_PACKAGE_ALIAS)
    bogus.__path__ = [r"C:\not\the\repo\book-knowledge\scripts"]
    monkeypatch.setitem(_sys.modules, ss._BK_PACKAGE_ALIAS, bogus)

    with pytest.raises(ss.SiblingNotFoundError):
        ss.load_book_knowledge_module("cozo_store")
