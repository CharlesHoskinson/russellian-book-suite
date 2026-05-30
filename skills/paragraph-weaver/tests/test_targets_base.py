# tests/test_targets_base.py
from __future__ import annotations

import pytest

from targets.base import Slot, GateResult, Target, register, get_target, REGISTRY


def test_slot_defaults_not_required():
    assert Slot("thesis").required is False
    assert Slot("thesis", required=True).required is True


def test_register_and_get():
    class Dummy(Target):
        name = "dummy"
        depth = "shallow"
        prose_policy = "none"

        def plan_template(self, goal):
            return [Slot("only")]

        def role_vocabulary(self):
            return ("x",)

        def order_objective(self, seq, graph, goal):
            return 0.0

        def gate_hook(self, artifacts):
            return GateResult(passed=True, mechanical={}, notes=[])

    register(Dummy())
    assert get_target("dummy").depth == "shallow"
    REGISTRY.pop("dummy")


def test_get_missing_raises():
    with pytest.raises(KeyError):
        get_target("nope")
