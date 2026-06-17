"""Tests for the pure defconstraint->CozoScript violation-rule compiler.

REQ-KG-003 / REQ-KG-012: a booklogic ``defconstraint`` form lowers to a
CozoScript rule that yields violation rows ``[focus_node, path, message]``,
reusing the :func:`compile_query` machinery (schema validation, clause/atom
lowering, filters, negation). The compiler is PURE: it reads only the schema
file, never a running store, and is deterministic.

Two layers of test:

* BYTE-IDENTICAL compile goldens (shape) — each of the five authored constraint
  EDN files compiles to a frozen ``.cozoscript`` golden. This pins the emitted
  shape so an accidental reordering or rename is caught.
* LIVE EXECUTION (semantics) — each compiled rule runs through a real
  ``CozoStore.in_memory`` and must fire ONLY on the violating row(s) and never
  on a conforming row. This proves the CozoScript is both syntactically valid
  and semantically the SHACL shape it ports.
"""
from pathlib import Path

import pytest

from scripts.booklogic_kg import compile_constraint
from scripts.cozo_store import CozoStore

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "assets" / "kg-schema.edn"
CONSTRAINTS = ROOT / "assets" / "kg-constraints"
GOLDEN = ROOT / "tests" / "golden" / "kg-constraints"

# The six active constraints. chapter-cites-verified was activated in P2.3 (the
# Cozo-backed validate_shacl) once kg-schema.edn gained a :chapter-section entity;
# see assets/kg-constraints/_DEFERRED.md.
CONSTRAINT_NAMES = [
    "status-enum",
    "confidence-range",
    "text-cardinality",
    "source-span-present",
    "verified-derives",
    "chapter-cites-verified",
]


def _edn(name: str) -> str:
    return (CONSTRAINTS / f"{name}.edn").read_text(encoding="utf-8")


# -- byte-identical compile goldens (shape) --------------------------------


@pytest.mark.parametrize("name", CONSTRAINT_NAMES)
def test_compile_golden(name):
    out = compile_constraint(_edn(name), SCHEMA)
    expected = (GOLDEN / f"{name}.cozoscript").read_text(encoding="utf-8")
    assert out == expected


# -- purity / shape --------------------------------------------------------


def test_compile_constraint_without_store():
    # Purity: compiling needs no Cozo instance, only the schema file. The result
    # is a CozoScript rule string ``?[...] := ...``.
    out = compile_constraint(_edn("source-span-present"), SCHEMA)
    assert isinstance(out, str)
    assert "?[focus_node, path_node, message] :=" in out


@pytest.mark.parametrize("name", CONSTRAINT_NAMES)
def test_compile_constraint_deterministic(name):
    edn = _edn(name)
    assert compile_constraint(edn, SCHEMA) == compile_constraint(edn, SCHEMA)


# -- error paths -----------------------------------------------------------


def test_undeclared_entity_raises():
    edn = (
        '(defconstraint :bad :message "m" :path "" '
        ':where [[?g :ghost/id ?focus]])'
    )
    with pytest.raises(ValueError) as exc:
        compile_constraint(edn, SCHEMA)
    assert "ghost" in str(exc.value)


def test_missing_message_raises():
    edn = (
        '(defconstraint :bad :path "" '
        ':where [[?c :claim/id ?focus]])'
    )
    with pytest.raises(ValueError) as exc:
        compile_constraint(edn, SCHEMA)
    assert "message" in str(exc.value).lower()


def test_missing_path_raises():
    edn = '(defconstraint :bad :message "m" :where [[?c :claim/id ?focus]])'
    with pytest.raises(ValueError) as exc:
        compile_constraint(edn, SCHEMA)
    assert "path" in str(exc.value).lower()


def test_missing_where_raises():
    edn = '(defconstraint :bad :message "m" :path "")'
    with pytest.raises(ValueError) as exc:
        compile_constraint(edn, SCHEMA)
    assert "where" in str(exc.value).lower()


def test_find_present_raises():
    edn = (
        '(defconstraint :bad :message "m" :path "" :find [?focus] '
        ':where [[?c :claim/id ?focus]])'
    )
    with pytest.raises(ValueError) as exc:
        compile_constraint(edn, SCHEMA)
    assert "find" in str(exc.value).lower()


def test_where_without_focus_raises():
    # :where must bind a ?focus variable (the violation's focus node).
    edn = (
        '(defconstraint :bad :message "m" :path "" '
        ':where [[?c :claim/id ?other]])'
    )
    with pytest.raises(ValueError) as exc:
        compile_constraint(edn, SCHEMA)
    assert "focus" in str(exc.value).lower()


def test_not_a_defconstraint_raises():
    edn = '(defquery :x :find [?focus] :where [[?c :claim/id ?focus]])'
    with pytest.raises(ValueError) as exc:
        compile_constraint(edn, SCHEMA)
    assert "defconstraint" in str(exc.value).lower()


# -- live execution (semantics) --------------------------------------------


def _focus_nodes(rows):
    """Violation rows are [focus_node, path, message]; project the focus ids."""
    return sorted(r[0] for r in rows)


def test_status_enum_executes():
    # Fires when status is OUTSIDE the 5-value vocabulary; conforming statuses
    # (and the null-status row, dropped by the !is_null guard) do not fire.
    script = compile_constraint(_edn("status-enum"), SCHEMA)
    store = CozoStore.in_memory(schema_path=SCHEMA)
    store.load("claim", [
        {"id": "c-unknown", "status": "unknown"},     # violation
        {"id": "c-verified", "status": "verified"},   # conforms
        {"id": "c-proposed", "status": "proposed"},   # conforms
        {"id": "c-disputed", "status": "disputed"},   # conforms
        {"id": "c-superseded", "status": "superseded"},  # conforms
        {"id": "c-refuted", "status": "refuted"},     # conforms
        {"id": "c-null"},                             # null status -> dropped
    ])
    rows = store.query(script)
    assert _focus_nodes(rows) == ["c-unknown"]
    # The row carries the SHACL path and a message.
    assert rows[0][1] == "https://example.org/book-knowledge#status"
    assert rows[0][2]


def test_confidence_range_executes():
    # Fires on confidence > 1.0 (the case the violating fixture injects: 1.5);
    # in-range and null-confidence rows do not fire.
    script = compile_constraint(_edn("confidence-range"), SCHEMA)
    store = CozoStore.in_memory(schema_path=SCHEMA)
    store.load("claim", [
        {"id": "c-hi", "confidence": 1.5},    # violation
        {"id": "c-ok", "confidence": 0.8},    # conforms
        {"id": "c-edge", "confidence": 1.0},  # conforms (<= 1.0)
        {"id": "c-null"},                     # null -> dropped
    ])
    rows = store.query(script)
    assert _focus_nodes(rows) == ["c-hi"]
    assert rows[0][1] == "https://example.org/book-knowledge#confidence"


def test_text_cardinality_executes():
    # minCount(text) >= 1 via negation: fires when a claim has NO non-null
    # canonical-text; a present (even empty-string) value conforms.
    script = compile_constraint(_edn("text-cardinality"), SCHEMA)
    store = CozoStore.in_memory(schema_path=SCHEMA)
    store.load("claim", [
        {"id": "c-no-text"},                            # violation (null)
        {"id": "c-has-text", "canonical-text": "hi"},   # conforms
    ])
    rows = store.query(script)
    assert _focus_nodes(rows) == ["c-no-text"]
    assert rows[0][1] == "https://schema.org/text"


def test_source_span_present_executes():
    # minCount(hasSourceSpan) >= 1 via negation: fires when NO source-span row
    # back-references the claim, regardless of status.
    script = compile_constraint(_edn("source-span-present"), SCHEMA)
    store = CozoStore.in_memory(schema_path=SCHEMA)
    store.load("claim", [
        {"id": "c-with-span", "status": "verified"},
        {"id": "c-no-span", "status": "verified"},      # violation
        {"id": "c-proposed-no-span", "status": "proposed"},  # violation (any status)
    ])
    store.load("source-span", [{"id": "s1", "claim-id": "c-with-span"}])
    rows = store.query(script)
    assert _focus_nodes(rows) == ["c-no-span", "c-proposed-no-span"]
    # Order-independent: every violation row carries the same path + message.
    assert all(
        r[1] == "https://example.org/book-knowledge#hasSourceSpan" for r in rows
    )
    assert all(r[2] for r in rows)


def test_not_binding_same_var_twice_dedupes_helper_head():
    # A :not group that binds the SAME env var (?focus) in two columns, plus a
    # free var that forces the helper-rule (minCount-via-negation) path. The
    # projected helper head must list ``focus`` ONCE, not ``focus, focus``
    # (which would be invalid CozoScript: a rule head with a duplicate var).
    edn = (
        '(defconstraint :dup '
        ':message "m" '
        ':path "" '
        ':where [[?c :claim/id ?focus]] '
        ':not [[?cf :claim-conflict/claim-id ?focus] '
        '[?cf :claim-conflict/other-id ?focus] '
        '[?cf :claim-conflict/id ?cfid]])'
    )
    script = compile_constraint(edn, SCHEMA)
    assert "present_0[focus]" in script
    assert "present_0[focus, focus]" not in script
    # And it executes against a live store without error.
    store = CozoStore.in_memory(schema_path=SCHEMA)
    store.load("claim", [{"id": "c-1"}])
    rows = store.query(script)
    assert isinstance(rows, list)


def test_verified_derives_executes():
    # The sh:sparql shape: a VERIFIED claim with no source-span. A verified claim
    # WITH a span conforms; a proposed claim with no span is out of scope.
    script = compile_constraint(_edn("verified-derives"), SCHEMA)
    store = CozoStore.in_memory(schema_path=SCHEMA)
    store.load("claim", [
        {"id": "v-with-source", "status": "verified"},   # conforms
        {"id": "v-no-source", "status": "verified"},      # violation
        {"id": "p-no-source", "status": "proposed"},      # out of scope
    ])
    store.load("source-span", [{"id": "s1", "claim-id": "v-with-source"}])
    rows = store.query(script)
    assert _focus_nodes(rows) == ["v-no-source"]
    assert rows[0][1] == ""  # path "" matches the C0.2 golden
    assert rows[0][2] == (
        "Verified claims must derive from at least one source-span entity."
    )


def test_chapter_cites_verified_executes():
    # The tbf:ChapterSectionShape sh:sparql shape: a chapter section that cites a
    # NON-verified claim fires; a section citing a verified claim conforms.
    script = compile_constraint(_edn("chapter-cites-verified"), SCHEMA)
    store = CozoStore.in_memory(schema_path=SCHEMA)
    store.load("claim", [
        {"id": "c-verified", "status": "verified"},
        {"id": "c-proposed", "status": "proposed"},
    ])
    store.load("chapter-section", [
        {"id": "sec-bad", "uses-claim-id": "c-proposed"},   # violation
        {"id": "sec-ok", "uses-claim-id": "c-verified"},    # conforms
    ])
    rows = store.query(script)
    assert _focus_nodes(rows) == ["sec-bad"]
    assert rows[0][1] == ""  # path "" (sh:sparql shape, no sh:path)
    assert rows[0][2] == "Chapter sections must only cite verified claims."
