# targets/emotion.py
"""SHALLOW stub: proves the Target interface for an emotional-arc goal.

v1 carries no valence pipeline; order_objective is trivial and the gate emits a
not-yet-deep warning. The deep valence-curve implementation is a v1.5 task.
"""
from __future__ import annotations

from engine.graph import WeaveGraph
from targets.base import Slot, GateResult, Target, register


class EmotionTarget(Target):
    name = "emotion"
    depth = "shallow"
    prose_policy = "none"

    def plan_template(self, goal: dict) -> list[Slot]:
        return [Slot("establish", required=True), Slot("tension"), Slot("resolve", required=True)]

    def role_vocabulary(self) -> tuple[str, ...]:
        return ("low", "neutral", "high")

    def order_objective(self, seq: list[str], graph: WeaveGraph, goal: dict) -> float:
        return 0.0

    def gate_hook(self, artifacts: dict) -> GateResult:
        return GateResult(passed=True, mechanical={}, notes=["SHALLOW: emotion target is not-yet-deep in v1"])


register(EmotionTarget())
