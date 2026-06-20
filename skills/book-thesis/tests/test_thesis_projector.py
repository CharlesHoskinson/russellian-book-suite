"""P3.1 — project the thesis YAML spine into the shared Cozo store (REQ-KG-016).

The thesis projector is the EDN-front/Cozo-back counterpart of compile_thesis's
RDF emit: it reads ``thesis/<book-id>.yaml`` and loads the root thesis node, its
sub-arguments, and its invariants into book-knowledge's Cozo ``thesis-node`` /
``sub-argument`` / ``invariant`` relations (reached via the P3.0 sibling bridge).
The YAML is read-only; the projection is deterministic. P3.2 runs the D9-D11
consistency pass over these rows.

The root thesis node is keyed ``"thesis"`` so a sub-argument's ``parent`` (which
defaults to / normalizes ``thesis``) joins it — the relational form of
compile_thesis's ``:supports :Thesis`` edge.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sibling_skills import book_knowledge_root, load_book_knowledge_module
from scripts.project_thesis_cozo import project_thesis

from tests.fixtures.violating_thesis import build_violating_thesis

pytestmark = pytest.mark.windows_canary


def _store():
    """A fresh in-memory Cozo store built from book-knowledge's shared schema."""
    cozo_store = load_book_knowledge_module("cozo_store")
    schema = book_knowledge_root() / "assets" / "kg-schema.edn"
    return cozo_store.CozoStore.in_memory(schema_path=schema)


def _q(store, defquery: str):
    return store.query_edn(defquery)


def test_projects_thesis_node(tmp_path):
    ws = build_violating_thesis(tmp_path)
    store = _store()
    project_thesis(ws, store, "violating")
    rows = _q(store, "(defquery :tn :find [?id ?st ?pol] "
                     ":where [[?t :thesis-node/id ?id] "
                     "[?t :thesis-node/statement ?st] "
                     "[?t :thesis-node/polarity ?pol]])")
    assert len(rows) == 1
    assert rows[0][0] == "thesis"
    assert "deliberately-violating thesis" in rows[0][1]
    assert rows[0][2] == "descriptive"


def test_projects_sub_arguments_with_parent(tmp_path):
    ws = build_violating_thesis(tmp_path)
    store = _store()
    project_thesis(ws, store, "violating")
    rows = _q(store, "(defquery :sa :find [?id ?parent] "
                     ":where [[?s :sub-argument/id ?id] "
                     "[?s :sub-argument/parent ?parent]])")
    assert {(r[0], r[1]) for r in rows} == {
        ("first-leg", "thesis"),
        ("second-leg", "thesis"),
    }


def test_projects_invariant_with_parsed_subject_and_pinned_value(tmp_path):
    ws = build_violating_thesis(tmp_path)
    store = _store()
    project_thesis(ws, store, "violating")
    rows = _q(store, "(defquery :inv :find [?id ?subj ?pin] "
                     ":where [[?i :invariant/id ?id] "
                     "[?i :invariant/subject ?subj] "
                     "[?i :invariant/pinned-value ?pin]])")
    # parish-count's formal is `... N != 9` -> subject parish_count, pinned 9.
    assert rows == [["parish-count", "parish_count", "9"]]


def test_infers_book_id_from_single_thesis_yaml(tmp_path):
    ws = build_violating_thesis(tmp_path)
    store = _store()
    project_thesis(ws, store)  # book_id inferred (only violating.yaml present)
    rows = _q(store, "(defquery :tn :find [?id] :where [[?t :thesis-node/id ?id]])")
    assert [r[0] for r in rows] == ["thesis"]


def test_yaml_is_untouched(tmp_path):
    ws = build_violating_thesis(tmp_path)
    yaml_path = ws / "thesis" / "violating.yaml"
    before = yaml_path.read_bytes()
    project_thesis(ws, _store(), "violating")
    assert yaml_path.read_bytes() == before


def test_projection_is_deterministic(tmp_path):
    ws = build_violating_thesis(tmp_path)

    def projected_rows():
        store = _store()
        project_thesis(ws, store, "violating")
        return sorted(
            _q(store, "(defquery :all :find [?id ?parent] "
                      ":where [[?s :sub-argument/id ?id] "
                      "[?s :sub-argument/parent ?parent]])")
        )

    assert projected_rows() == projected_rows()
