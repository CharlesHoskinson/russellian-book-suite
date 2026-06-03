from __future__ import annotations

import pytest
pytestmark = pytest.mark.windows_canary

from engine.graph import Node, WeaveGraph
from engine.feasibility import check_feasibility
from targets.base import Slot


_SLOTS = [Slot("thesis", required=True), Slot("evidence", required=True), Slot("aside")]


def test_passes_when_required_slots_filled_and_connected():
    g = WeaveGraph(nodes=[
        Node(id="A", text="x", entities=("shell",), bound_slot="thesis"),
        Node(id="B", text="y", entities=("shell", "foot"), bound_slot="evidence"),
    ])
    res = check_feasibility(g, _SLOTS)
    assert res.ok and res.reasons == []


def test_refuses_when_required_slot_unfilled():
    g = WeaveGraph(nodes=[Node(id="A", text="x", entities=("shell",), bound_slot="thesis")])
    res = check_feasibility(g, _SLOTS)
    assert not res.ok
    assert any("evidence" in r for r in res.reasons)


def test_refuses_when_entity_graph_disconnected():
    g = WeaveGraph(nodes=[
        Node(id="A", text="x", entities=("shell",), bound_slot="thesis"),
        Node(id="B", text="y", entities=("planet",), bound_slot="evidence"),
    ])
    res = check_feasibility(g, _SLOTS)
    assert not res.ok
    assert any("disconnected" in r for r in res.reasons)


def test_refuses_when_too_many_unbound():
    g = WeaveGraph(nodes=[
        Node(id="A", text="x", entities=("shell",), bound_slot="thesis"),
        Node(id="B", text="y", entities=("shell",), bound_slot="evidence"),
        Node(id="C", text="z", entities=("shell",), bound_slot=None),
        Node(id="D", text="w", entities=("shell",), bound_slot=None),
        Node(id="E", text="v", entities=("shell",), bound_slot=None),
    ])
    res = check_feasibility(g, _SLOTS, max_unbound_fraction=0.5)
    assert not res.ok
    assert any("unbound" in r for r in res.reasons)
