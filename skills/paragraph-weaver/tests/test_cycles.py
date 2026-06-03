# tests/test_cycles.py
from __future__ import annotations

import pytest
pytestmark = pytest.mark.windows_canary

from engine.graph import Node, Edge, WeaveGraph
from engine.cycles import find_cycles


def _g(edges):
    nodes = [Node(id=x, text=x) for x in ("a", "b", "c")]
    return WeaveGraph(nodes=nodes, edges=[Edge(src=s, dst=d) for s, d in edges])


def test_acyclic_returns_no_cycles():
    assert find_cycles(_g([("a", "b"), ("b", "c")])) == []


def test_two_cycle_detected():
    cycles = find_cycles(_g([("a", "b"), ("b", "a")]))
    assert len(cycles) == 1
    assert set(cycles[0]) == {"a", "b"}


def test_self_loop_detected():
    cycles = find_cycles(_g([("a", "a")]))
    assert cycles == [["a"]]
