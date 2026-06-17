"""Tests for the graphify graph.json -> Cozo loader (P4.1).

`project_graphify(path, store)` reads a graphify ``graph.json`` document and
loads its ``nodes`` into the ``code-node`` relation and its ``links`` into the
``code-edge`` relation, mapping field names from graphify's shape to the
schema's columns. ``rank``/``community`` are left null (an in-engine recompute,
P4.2, fills them). The loader is deterministic.
"""
from __future__ import annotations

from pathlib import Path

from scripts.cozo_store import CozoStore
from scripts.project_graphify import project_graphify

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "assets" / "kg-schema.edn"
FIXTURE = Path(__file__).parent / "fixtures" / "graphify-sample.json"


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
