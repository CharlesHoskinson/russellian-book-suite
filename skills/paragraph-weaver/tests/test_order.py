from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

from engine.graph import Node, Edge, WeaveGraph
from engine.order import all_topological_orders, order_paragraphs


def _g(edges):
    nodes = [Node(id=x, text=x) for x in ("a", "b", "c")]
    return WeaveGraph(nodes=nodes, edges=[Edge(src=s, dst=d) for s, d in edges])


def test_topological_orders_respect_precedence():
    orders = all_topological_orders(["a", "b", "c"], [Edge(src="a", dst="b")])
    for o in orders:
        assert o.index("a") < o.index("b")
    # No order may violate the single precedence edge.
    assert ["b", "a", "c"] not in orders


def test_order_paragraphs_minimizes_objective_subject_to_precedence():
    g = _g([("a", "b")])  # a before b is hard.

    # Objective prefers c first; ties broken by lexical order via stable min.
    def objective(seq):
        return 0.0 if seq[0] == "c" else 1.0

    result = order_paragraphs(g, objective)
    assert result[0] == "c"
    assert result.index("a") < result.index("b")


def test_large_graph_falls_back_to_single_topo_order():
    nodes = [Node(id=str(i), text=str(i)) for i in range(12)]
    g = WeaveGraph(nodes=nodes, edges=[])
    result = order_paragraphs(g, lambda seq: 0.0, max_exact=9)
    assert sorted(result) == sorted(n.id for n in nodes)
