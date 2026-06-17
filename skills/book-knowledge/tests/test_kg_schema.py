"""Contract tests for the unified EDN graph schema (REQ-KG-001).

``assets/kg-schema.edn`` is the homoiconic source of truth for the unified
knowledge graph (claims + thesis + code graph). It is distinct from
``assets/claim-record.schema.json``, which guards ledger-write shape.
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import edn_format
import pytest


def _is_seq(value) -> bool:
    """True for an EDN list/vector (incl. edn_format.ImmutableList), not a str."""
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "assets" / "kg-schema.edn"

EXPECTED_ENTITIES = {
    "claim",
    "source-span",
    "claim-chapter",
    "chapter",
    "claim-conflict",
    "counter-claim",
    "rebuttal-window-ok",
    "source",
    "thesis-node",
    "sub-argument",
    "invariant",
    "wiki-page",
    "chapter-wiki-ref",
    "code-node",
    "code-edge",
    "community",
    "code-claim-link",
    "chapter-section",
}


def _kw(name: str) -> edn_format.Keyword:
    return edn_format.Keyword(name)


def _name(value) -> str:
    """Normalize an edn Keyword/Symbol (or str) to its bare name."""
    return getattr(value, "name", value)


def _normalize_keys(mapping) -> dict:
    """Return a plain dict keyed by bare keyword names."""
    return {_name(k): v for k, v in mapping.items()}


@pytest.fixture(scope="module")
def schema() -> dict:
    text = SCHEMA_PATH.read_text(encoding="utf-8")
    return edn_format.loads(text)


@pytest.fixture(scope="module")
def entities(schema) -> dict:
    top = _normalize_keys(schema)
    assert "entities" in top, "schema must have an :entities map"
    return _normalize_keys(top["entities"])


def test_schema_declares_all_entities_attrs_relations(entities):
    # All named entities are present.
    assert set(entities) == EXPECTED_ENTITIES, (
        f"entity set mismatch: {set(entities) ^ EXPECTED_ENTITIES}"
    )

    for ename, spec in entities.items():
        espec = _normalize_keys(spec)

        # Each entity spec has a non-empty :attrs list.
        assert "attrs" in espec, f"{ename}: missing :attrs"
        attrs = espec["attrs"]
        assert _is_seq(attrs), f"{ename}: :attrs must be a list"
        assert len(attrs) > 0, f"{ename}: :attrs must be non-empty"

        # Each entity spec has a :relations key (list, possibly empty).
        assert "relations" in espec, f"{ename}: missing :relations"
        relations = espec["relations"]
        assert _is_seq(relations), f"{ename}: :relations must be a list"

    # At least claim and code-node declare >= 1 relation.
    for ename in ("claim", "code-node"):
        rels = _normalize_keys(entities[ename])["relations"]
        assert len(rels) >= 1, f"{ename} must declare at least one relation"


def test_attr_names_are_kebab_case_keywords(entities):
    """Attr and relation names must be clean kebab-case keywords (REQ-KG-001).

    Cozo relation creation (REQ-KG-011) and the EDN->CozoScript compiler
    (REQ-KG-003) depend on stable kebab-case keyword names.
    """
    for ename, spec in entities.items():
        espec = _normalize_keys(spec)
        for attr in espec["attrs"]:
            assert isinstance(attr, edn_format.Keyword), (
                f"{ename}: attr {attr!r} must be an EDN keyword"
            )
            bare = _name(attr)
            assert bare == bare.lower(), f"{ename}: attr {bare} not lowercase"
            assert "_" not in bare, f"{ename}: attr {bare} must be kebab-case"
        for rel in espec["relations"]:
            assert _is_seq(rel) and len(rel) == 2, (
                f"{ename}: relation {rel!r} must be a [verb target] pair"
            )
            verb, target = rel
            assert isinstance(verb, edn_format.Keyword), (
                f"{ename}: relation verb {verb!r} must be a keyword"
            )
            assert isinstance(target, edn_format.Keyword), (
                f"{ename}: relation target {target!r} must be a keyword"
            )
            # Relation targets must reference declared entities.
            assert _name(target) in EXPECTED_ENTITIES, (
                f"{ename}: relation target {_name(target)} is not a declared entity"
            )
