# tests/test_argument.py
from __future__ import annotations

import pytest
pytestmark = pytest.mark.windows_canary

from engine.graph import Node, WeaveGraph
from targets.argument import ArgumentTarget


def _graph():
    return WeaveGraph(nodes=[
        Node(id="A", text="Thesis.", role="claim", bound_slot="thesis"),
        Node(id="B", text="Evidence.", role="premise", bound_slot="evidence"),
        Node(id="C", text="Conclusion.", role="conclusion", bound_slot="conclusion"),
    ])


def test_plan_template_has_required_thesis_and_conclusion():
    slots = ArgumentTarget().plan_template({})
    by_name = {s.name: s for s in slots}
    assert by_name["thesis"].required and by_name["conclusion"].required
    assert by_name["concession"].required is False


def test_in_slot_order_beats_out_of_order():
    t = ArgumentTarget()
    g = _graph()
    in_order = t.order_objective(["A", "B", "C"], g, {})
    out_order = t.order_objective(["C", "A", "B"], g, {})
    assert in_order < out_order


def test_depth_and_prose_policy():
    t = ArgumentTarget()
    assert t.depth == "deep"
    assert t.prose_policy == "russellian-style"
