"""Tests for the graphify graph.json -> Cozo loader (P4.1).

`project_graphify(path, store)` reads a graphify ``graph.json`` document and
loads its ``nodes`` into the ``code-node`` relation and its ``links`` into the
``code-edge`` relation, mapping field names from graphify's shape to the
schema's columns. ``rank``/``community`` are left null (an in-engine recompute,
P4.2, fills them). The loader is deterministic.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.cozo_store import CozoStore
from scripts.project_graphify import project_graphify

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "assets" / "kg-schema.edn"
FIXTURE = Path(__file__).parent / "fixtures" / "graphify-sample.json"


def _write(tmp_path: Path, doc) -> Path:
    p = tmp_path / "graph.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


def test_loads_nodes_and_edges() -> None:
    """Nodes land in code-node and links land in code-edge with mapped fields."""
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_graphify(FIXTURE, store)

    # All fixture node ids are present as code-node rows (via the EDN seam).
    node_ids = sorted(
        r[0]
        for r in store.query_edn(
            "(defquery :n :find [?id] :where [[?c :code-node/id ?id]])"
        )
    )
    assert node_ids == ["fn_delta", "fn_gamma", "mod_alpha", "mod_beta"]

    # Labels mapped from graphify's ``label`` field.
    labels = {
        r[0]: r[1]
        for r in store.query_edn(
            "(defquery :n :find [?id ?label] "
            ":where [[?c :code-node/id ?id] [?c :code-node/label ?label]])"
        )
    }
    assert labels["mod_alpha"] == "alpha.py"
    assert labels["fn_gamma"] == "gamma()"

    source_files = {
        r[0]: r[1]
        for r in store.query(
            "?[id, source_file] := *code_node{id, source_file}"
        )
    }
    assert source_files["mod_alpha"] == "src/alpha.py"
    assert source_files["fn_gamma"] == "src/alpha.py"

    # rank/community left null until the recompute pass (P4.2).
    ranks = store.query("?[id, rank] := *code_node{id, rank}")
    assert all(row[1] is None for row in ranks)

    # All fixture links land in code-edge with relation->relationship mapping.
    edges = sorted(
        tuple(r)
        for r in store.query_edn(
            "(defquery :e :find [?s ?t ?rel] "
            ":where [[?e :code-edge/source-id ?s] "
            "[?e :code-edge/target-id ?t] "
            "[?e :code-edge/relationship ?rel]])"
        )
    )
    assert edges == [
        ("fn_gamma", "fn_delta", "calls"),
        ("mod_alpha", "fn_gamma", "contains"),
        ("mod_alpha", "mod_beta", "imports"),
        ("mod_beta", "fn_delta", "contains"),
    ]

    # Weight carried through as a real Float (typed column).
    heavy = store.query("?[source_id] := *code_edge{source_id, weight}, weight > 1.5")
    assert heavy == [["fn_gamma"]]


def test_idempotent_reprojection() -> None:
    """Re-running the loader upserts rather than duplicating rows."""
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_graphify(FIXTURE, store)
    project_graphify(FIXTURE, store)

    n_nodes = store.query("?[count(id)] := *code_node{id}")
    assert n_nodes == [[4]]
    n_edges = store.query("?[count(source_id)] := *code_edge{source_id}")
    assert n_edges == [[4]]


# --- F1: structural validation (fail fast on malformed graphify docs) ---------
# A missing file or a non-graphify JSON must NOT produce a silently-empty/partial
# projection. But validation is calibrated against the REAL graph.json (39k nodes,
# 818k links), which legitimately carries duplicate node ids and ~7.5k dangling
# edges (graphify's ``ref_*`` reference targets) — those are TOLERATED, not errors.


def test_rejects_doc_missing_nodes_key(tmp_path: Path) -> None:
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    with pytest.raises(ValueError, match="nodes"):
        project_graphify(_write(tmp_path, {"links": []}), store)


def test_rejects_doc_missing_links_key(tmp_path: Path) -> None:
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    with pytest.raises(ValueError, match="links"):
        project_graphify(_write(tmp_path, {"nodes": []}), store)


def test_rejects_nodes_not_a_list(tmp_path: Path) -> None:
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    with pytest.raises(ValueError, match="nodes"):
        project_graphify(_write(tmp_path, {"nodes": {}, "links": []}), store)


def test_rejects_node_missing_id(tmp_path: Path) -> None:
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    doc = {"nodes": [{"label": "no id"}], "links": []}
    with pytest.raises(ValueError, match="node.*id"):
        project_graphify(_write(tmp_path, doc), store)


def test_rejects_node_empty_id(tmp_path: Path) -> None:
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    doc = {"nodes": [{"id": ""}], "links": []}
    with pytest.raises(ValueError, match="node.*id"):
        project_graphify(_write(tmp_path, doc), store)


def test_rejects_link_missing_endpoint(tmp_path: Path) -> None:
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    doc = {
        "nodes": [{"id": "n1"}, {"id": "n2"}],
        "links": [{"source": "n1", "relation": "calls"}],
    }
    with pytest.raises(ValueError, match="link.*target"):
        project_graphify(_write(tmp_path, doc), store)


def test_rejects_link_missing_relation(tmp_path: Path) -> None:
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    doc = {
        "nodes": [{"id": "n1"}, {"id": "n2"}],
        "links": [{"source": "n1", "target": "n2"}],
    }
    with pytest.raises(ValueError, match="link.*relation"):
        project_graphify(_write(tmp_path, doc), store)


def test_rejects_non_numeric_weight(tmp_path: Path) -> None:
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    doc = {
        "nodes": [{"id": "n1"}, {"id": "n2"}],
        "links": [{"source": "n1", "target": "n2", "relation": "calls", "weight": "heavy"}],
    }
    with pytest.raises(ValueError, match="weight"):
        project_graphify(_write(tmp_path, doc), store)


def test_tolerates_real_graphify_quirks(tmp_path: Path) -> None:
    """Duplicate node ids and dangling edges are REAL graphify output — load, don't raise.

    The real graph.json has duplicate ids (last-write-wins under :put) and ~7.5k
    edges whose target is a ``ref_*`` node outside the node set. Rejecting these
    would break ingestion of actual graphify output.
    """
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    doc = {
        "nodes": [
            {"id": "dup", "label": "first"},
            {"id": "dup", "label": "second"},
            {"id": "n2", "label": "two"},
        ],
        "links": [
            {"source": "n2", "target": "ref_external", "relation": "references", "weight": 1.0},
        ],
    }
    project_graphify(_write(tmp_path, doc), store)  # must not raise

    n_nodes = store.query("?[count(id)] := *code_node{id}")
    assert n_nodes == [[2]]  # dup collapsed to one row
    n_edges = store.query("?[count(source_id)] := *code_edge{source_id}")
    assert n_edges == [[1]]  # dangling edge still loaded
