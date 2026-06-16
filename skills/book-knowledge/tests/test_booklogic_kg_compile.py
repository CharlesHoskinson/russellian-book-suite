"""Tests for the pure EDN->CozoScript compiler (REQ-KG-003).

These prove the minimal subset of the booklogic defquery grammar that P0.5
supports: ?find vars, a :where of triples sharing an entity var (grouped into
one body atom with literal-equality filters), and an optional :not negation.
The compiler is PURE: it reads only the schema file, never a running store.
"""
from pathlib import Path

import pytest

from scripts.booklogic_kg import compile_query

SCHEMA = Path(__file__).resolve().parents[1] / "assets" / "kg-schema.edn"


def test_defquery_golden():
    edn = (
        '(defquery :verified-ids '
        ':find [?id] '
        ':where [[?c :claim/id ?id] [?c :claim/status "verified"]])'
    )
    expected = '?[id] := *claim{id, status}, status == "verified"'
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
    assert out == '?[id] := *claim{id}'


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
    # FILTER NOT EXISTS { ?claim prov:wasDerivedFrom ?src } shape: a :not clause
    # over a relation becomes a Cozo `not *relation{...}`.
    edn = (
        '(defquery :unsupported '
        ':find [?id] '
        ':where [[?c :claim/id ?id] [?c :claim/status "verified"]] '
        ':not [[?s :source-span/id ?id]])'
    )
    out = compile_query(edn, SCHEMA)
    expected = (
        '?[id] := *claim{id, status}, status == "verified", '
        'not *source_span{id}'
    )
    assert out == expected
