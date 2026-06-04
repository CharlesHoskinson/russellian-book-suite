# targets/narrative.py
"""SHALLOW stub: proves the Target interface for a story-arc goal.

v1 carries no causal-DAG or tension model; order_objective is trivial and the
gate emits a not-yet-deep warning. The deep implementation is a v2 task.
"""
from __future__ import annotations

from engine.graph import WeaveGraph
from targets.base import Slot, GateResult, Target, register


class NarrativeTarget(Target):
    name = "narrative"
    depth = "shallow"
    prose_policy = "none"

    def plan_template(self, goal: dict) -> list[Slot]:
        return [
            Slot("exposition", required=True),
            Slot("rising"),
            Slot("climax", required=True),
            Slot("falling"),
            Slot("close", required=True),
        ]

    def role_vocabulary(self) -> tuple[str, ...]:
        return ("setup", "develop", "turn", "resolve")

    def order_objective(self, seq: list[str], graph: WeaveGraph, goal: dict) -> float:
        return 0.0

    def gate_hook(self, artifacts: dict) -> GateResult:
        return GateResult(passed=True, mechanical={}, notes=["SHALLOW: narrative target is not-yet-deep in v1"])


register(NarrativeTarget())
