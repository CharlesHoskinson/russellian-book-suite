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

from scripts.booklogic_kg import _format_literal, compile_query
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


def test_format_literal_rejects_unrepresentable_string():
    """A string literal containing a double-quote or backslash is NOT safely
    representable as a CozoScript inline literal in the embedded Cozo build: the
    escaped form (\\") is rejected by the parser. Reject at COMPILE time with a
    clear error rather than emit a script that fails opaquely at query time."""
    with pytest.raises(ValueError, match="not safely representable"):
        _format_literal('a "quote" x')
    with pytest.raises(ValueError, match="not safely representable"):
        _format_literal("a \\ slash")


def test_compiled_literal_query_actually_runs_against_store():
    """Regression for the literal approach: a compiled query carrying an ordinary
    string literal must PARSE/RUN against the embedded Cozo. A string-match-only
    test cannot catch that an escaped quote is parser-rejected."""
    edn = (
        "(defquery :t :find [?id] "
        ':where [[?c :claim/id ?id] [?c :claim/status "verified"]])'
    )
    out = compile_query(edn, SCHEMA)
    store = CozoStore.in_memory(schema_path=SCHEMA)
    assert store.query(out) == []


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


def test_filter_comparison_golden():
    # :filter lowers an ordered comparison to an inline expr atom on the bound
    # var, guarded by !is_null (a nullable column would error Cozo on a null
    # cell). The numeric literal stays UNQUOTED so it compares against the Float.
    edn = (
        '(defquery :floor '
        ':find [?id ?p] '
        ':where [[?c :claim/id ?id] [?c :claim/p-posterior ?p]] '
        ':filter [[< ?p 0.4]])'
    )
    out = compile_query(edn, SCHEMA)
    expected = (
        '?[id, p] := *claim{id: id, p_posterior: p}, '
        '!is_null(p), p < 0.4'
    )
    assert out == expected


def test_filter_unknown_comparator_raises():
    edn = (
        '(defquery :bad :find [?p] '
        ':where [[?c :claim/p-posterior ?p]] :filter [[== ?p 0.4]])'
    )
    with pytest.raises(ValueError) as exc:
        compile_query(edn, SCHEMA)
    assert "comparator" in str(exc.value).lower()


def test_filter_unbound_var_raises():
    # The compared var must be bound by :where; an unknown var is a clear error.
    edn = (
        '(defquery :bad :find [?p] '
        ':where [[?c :claim/p-posterior ?p]] :filter [[< ?q 0.4]])'
    )
    with pytest.raises(ValueError) as exc:
        compile_query(edn, SCHEMA)
    assert "not bound" in str(exc.value)


def test_filter_var_vs_var_golden():
    # A :filter RHS may be another bound ?var (var-vs-var comparison). Both
    # operands are guarded with !is_null, then compared inline. This is what
    # stale_after_source_refresh needs: ?src_date > ?claim_date.
    edn = (
        '(defquery :vv '
        ':find [?p ?q] '
        ':where [[?c :claim/p-posterior ?p] [?c :claim/p-prior ?q]] '
        ':filter [[> ?p ?q]])'
    )
    out = compile_query(edn, SCHEMA)
    expected = (
        '?[p, q] := *claim{p_posterior: p, p_prior: q}, '
        '!is_null(p), !is_null(q), p > q'
    )
    assert out == expected


def test_filter_var_vs_var_unbound_rhs_raises():
    # The RHS var must also be bound by :where; an unknown RHS var is an error.
    edn = (
        '(defquery :bad :find [?p] '
        ':where [[?c :claim/p-posterior ?p]] :filter [[> ?p ?q]])'
    )
    with pytest.raises(ValueError) as exc:
        compile_query(edn, SCHEMA)
    assert "not bound" in str(exc.value)


def test_filter_var_vs_var_executes(tmp_path=None):
    # Semantics: only the row whose p_posterior strictly exceeds p_prior returns;
    # the equal-valued and the null-operand rows are dropped (the !is_null guards).
    edn = (
        '(defquery :vv :find [?id] '
        ':where [[?c :claim/id ?id] [?c :claim/p-posterior ?p] '
        '[?c :claim/p-prior ?q]] '
        ':filter [[> ?p ?q]])'
    )
    script = compile_query(edn, SCHEMA)
    store = CozoStore.in_memory(schema_path=SCHEMA)
    store.load("claim", [
        {"id": "rose", "p-posterior": 0.9, "p-prior": 0.3},   # > -> returns
        {"id": "flat", "p-posterior": 0.5, "p-prior": 0.5},   # == -> excluded
        {"id": "fell", "p-posterior": 0.2, "p-prior": 0.8},   # < -> excluded
    ])
    rows = store.query(script)
    assert rows == [["rose"]]


def test_filter_malformed_arity_raises():
    edn = (
        '(defquery :bad :find [?p] '
        ':where [[?c :claim/p-posterior ?p]] :filter [[< ?p]])'
    )
    with pytest.raises(ValueError) as exc:
        compile_query(edn, SCHEMA)
    assert "filter" in str(exc.value).lower()


def test_filter_excludes_above_and_null(tmp_path=None):
    # Semantics: only the sub-floor, non-null claim returns. The above-floor
    # claim fails the comparison; the null-posterior claim is dropped by the
    # !is_null guard rather than erroring (faithful to SPARQL triple existence).
    edn = (
        '(defquery :floor '
        ':find [?id ?p] '
        ':where [[?c :claim/id ?id] [?c :claim/p-posterior ?p]] '
        ':filter [[< ?p 0.4]])'
    )
    script = compile_query(edn, SCHEMA)

    store = CozoStore.in_memory(schema_path=SCHEMA)
    store.load("claim", [
        {"id": "low", "p-posterior": 0.3},
        {"id": "high", "p-posterior": 0.9},
        {"id": "none"},  # null p_posterior -> excluded, not an error
    ])
    rows = store.query(script)
    assert rows == [["low", 0.3]]


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
