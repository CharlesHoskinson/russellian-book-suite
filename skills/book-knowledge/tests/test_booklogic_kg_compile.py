"""Tests for the pure EDN->CozoScript compiler (REQ-KG-003).

These prove the subset of the booklogic defquery grammar that P0.5 supports:
?find vars, a :where of triples (each binding an entity-attr column to an EDN
variable, with shared variables unifying across atoms as a join), literal
where-values lowered to inline matches, and an optional :not negation that
threads a bound variable. The compiler is PURE: it reads only the schema file,
never a running store.

The string goldens pin the emitted CozoScript shape; the EXECUTION tests run the
emitted script through a real CozoStore and assert the returned ROWS, so a
compiler that emits syntactically plausible but semantically wrong CozoScript
(e.g. dropping the find-variable binding, or failing to unify a join var) is
caught.
"""
from pathlib import Path

import pytest

from scripts.booklogic_kg import compile_query
from scripts.cozo_store import CozoStore

SCHEMA = Path(__file__).resolve().parents[1] / "assets" / "kg-schema.edn"


# -- string goldens (shape) ------------------------------------------------


def test_defquery_golden():
    edn = (
        '(defquery :verified-ids '
        ':find [?id] '
        ':where [[?c :claim/id ?id] [?c :claim/status "verified"]])'
    )
    expected = '?[id] := *claim{id: id, status: "verified"}'
    out = compile_query(edn, SCHEMA)
    assert out == expected
    # Re-compiling is byte-identical (determinism).
    assert compile_query(edn, SCHEMA) == out


def test_compile_without_store():
    # Purity: no Cozo instance, no store -- the function only reads the schema
    # file and returns a string.
    edn = '(defquery :ids :find [?id] :where [[?c :claim/id ?id]])'
    out = compile_query(edn, SCHEMA)
    assert isinstance(out, str)
    assert out == '?[id] := *claim{id: id}'


def test_undeclared_entity_raises():
    edn = '(defquery :bad :find [?id] :where [[?g :ghost/id ?id]])'
    with pytest.raises(ValueError) as exc:
        compile_query(edn, SCHEMA)
    assert "ghost" in str(exc.value)


def test_undeclared_attr_raises():
    edn = '(defquery :bad :find [?x] :where [[?c :claim/nonsense ?x]])'
    with pytest.raises(ValueError) as exc:
        compile_query(edn, SCHEMA)
    assert "nonsense" in str(exc.value)


def test_negation_compiles():
    # "verified claims with no source span": the :not clause threads the bound
    # ?cid into a Cozo negation that unifies on claim_id.
    edn = (
        '(defquery :unsupported '
        ':find [?cid] '
        ':where [[?c :claim/id ?cid] [?c :claim/status "verified"]] '
        ':not [[?s :source-span/claim-id ?cid]])'
    )
    out = compile_query(edn, SCHEMA)
    expected = (
        '?[cid] := *claim{id: cid, status: "verified"}, '
        'not *source_span{claim_id: cid}'
    )
    assert out == expected


def test_malformed_triple_raises():
    # A triple must be [evar :entity/attr value]; a 2-element triple is a clear
    # ValueError, not an IndexError leaking from tuple unpacking.
    edn = '(defquery :bad :find [?id] :where [[?c :claim/id]])'
    with pytest.raises(ValueError) as exc:
        compile_query(edn, SCHEMA)
    assert "triple" in str(exc.value).lower()


# -- execution tests (semantics) -------------------------------------------


def test_find_var_differs_from_column():
    # The find variable (?theid) is NOT the column name (id). The compiler must
    # rename the column to the find var (*claim{id: theid}) so ?theid is a
    # genuinely bound body variable; only the verified claim's id returns.
    edn = (
        '(defquery :verified-ids '
        ':find [?theid] '
        ':where [[?c :claim/id ?theid] [?c :claim/status "verified"]])'
    )
    script = compile_query(edn, SCHEMA)

    store = CozoStore.in_memory(schema_path=SCHEMA)
    store.load("claim", [
        {"id": "c-verified", "status": "verified"},
        {"id": "c-proposed", "status": "proposed"},
    ])
    rows = store.query(script)
    assert rows == [["c-verified"]]


def test_join_unifies_shared_var():
    # A 2-relation join on a shared var (?cid) returns only the joined rows; a
    # claim with no matching span is excluded. This proves the compiler unifies
    # the shared variable rather than emitting two independent columns.
    edn = (
        '(defquery :claims-with-span '
        ':find [?cid] '
        ':where [[?c :claim/id ?cid] [?s :source-span/claim-id ?cid]])'
    )
    script = compile_query(edn, SCHEMA)

    store = CozoStore.in_memory(schema_path=SCHEMA)
    store.load("claim", [
        {"id": "c1", "status": "verified"},
        {"id": "c2", "status": "verified"},  # no span -> excluded
    ])
    store.load("source-span", [
        {"id": "s1", "claim-id": "c1"},
    ])
    rows = store.query(script)
    assert rows == [["c1"]]


def test_negation_excludes_matches():
    # "verified claims with no source-span": the verified claim WITH a span is
    # excluded by the negation; only the verified claim WITHOUT a span returns.
    edn = (
        '(defquery :unsupported '
        ':find [?cid] '
        ':where [[?c :claim/id ?cid] [?c :claim/status "verified"]] '
        ':not [[?s :source-span/claim-id ?cid]])'
    )
    script = compile_query(edn, SCHEMA)

    store = CozoStore.in_memory(schema_path=SCHEMA)
    store.load("claim", [
        {"id": "c-with-span", "status": "verified"},
        {"id": "c-without-span", "status": "verified"},
        {"id": "c-proposed", "status": "proposed"},  # not verified -> excluded
    ])
    store.load("source-span", [
        {"id": "s1", "claim-id": "c-with-span"},
    ])
    rows = store.query(script)
    assert rows == [["c-without-span"]]
