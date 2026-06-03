# tests/test_graph.py
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

from engine.graph import Node, Edge, WeaveGraph


def _graph():
    return WeaveGraph(
        nodes=[
            Node(id="p2", text="Second.", entities=("beta",), role="premise", bound_slot="evidence"),
            Node(id="p1", text="First.", entities=("alpha",), role="claim", bound_slot="thesis"),
        ],
        edges=[Edge(src="p1", dst="p2")],
    )


def test_node_lookup():
    g = _graph()
    assert g.node("p1").role == "claim"


def test_json_round_trip_preserves_data():
    g = _graph()
    g2 = WeaveGraph.from_json(g.to_json())
    assert g2.node("p2").entities == ("beta",)
    assert g2.edges[0].src == "p1"


def test_content_hash_is_order_independent_and_stable():
    g = _graph()
    # Reversed node order, same content → identical hash (canonical serialization).
    g_rev = WeaveGraph(nodes=list(reversed(g.nodes)), edges=list(g.edges))
    assert g.content_hash() == g_rev.content_hash()
    # Changing content changes the hash.
    g3 = WeaveGraph(nodes=g.nodes, edges=[Edge(src="p2", dst="p1")])
    assert g3.content_hash() != g.content_hash()
