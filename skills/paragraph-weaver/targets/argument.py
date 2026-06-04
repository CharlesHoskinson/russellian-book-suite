# targets/argument.py
"""Deep target: thread paragraphs toward a thesis (dispositio order).

order_objective is a soft penalty (lower = better):
  * slot-order conformance — penalize each paragraph whose planned slot rank
    falls before an already-placed higher slot (inversions vs the plan order).
  * edge-loading — penalize a strong paragraph (role claim/conclusion) landing in
    the middle third, per the persuasion-ordering literature (climax/anticlimax,
    never pyramidal). This is a SOFT penalty, never a hard constraint.
"""
from __future__ import annotations

from engine.graph import WeaveGraph
from engine.gate import score_gate
from targets.base import Slot, GateResult, Target, register

_PLAN = [
    Slot("thesis", required=True),
    Slot("evidence", required=True),
    Slot("concession", required=False),
    Slot("rebuttal", required=False),
    Slot("conclusion", required=True),
]
_STRONG_ROLES = {"claim", "conclusion"}


class ArgumentTarget(Target):
    name = "argument"
    depth = "deep"
    prose_policy = "russellian-style"

    def plan_template(self, goal: dict) -> list[Slot]:
        return list(_PLAN)

    def role_vocabulary(self) -> tuple[str, ...]:
        return ("claim", "premise", "warrant", "rebuttal", "conclusion")

    def order_objective(self, seq: list[str], graph: WeaveGraph, goal: dict) -> float:
        nodes = {n.id: n for n in graph.nodes}
        rank = {s.name: i for i, s in enumerate(_PLAN)}
        miss = len(_PLAN)
        penalty = 0.0
        highest = -1
        for nid in seq:
            r = rank.get(nodes[nid].bound_slot, miss)
            if r < highest:
                penalty += 1.0
            highest = max(highest, r)
        length = len(seq)
        for i, nid in enumerate(seq):
            if nodes[nid].role in _STRONG_ROLES and length:
                pos = i / length
                if 1 / 3 <= pos < 2 / 3:
                    penalty += 0.5
        return penalty

    def gate_hook(self, artifacts: dict) -> GateResult:
        return score_gate(artifacts)


register(ArgumentTarget())
