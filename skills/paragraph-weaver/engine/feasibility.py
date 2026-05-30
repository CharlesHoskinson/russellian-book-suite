"""Feasibility gate: the engine's ability to refuse.

Run AFTER bind, BEFORE order. If required slots are unfilled, too many paragraphs
are off-goal, or the entity graph is disconnected, the engine stops and emits a
diagnosis instead of threading garbage.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from engine.graph import WeaveGraph


@dataclass
class FeasibilityResult:
    ok: bool
    reasons: list[str] = field(default_factory=list)


def _connected(graph: WeaveGraph) -> bool:
    ids = [n.id for n in graph.nodes]
    if len(ids) <= 1:
        return True
    parent = {i: i for i in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    by_entity: dict[str, list[str]] = {}
    for n in graph.nodes:
        for e in n.entities:
            by_entity.setdefault(e, []).append(n.id)
    for members in by_entity.values():
        for other in members[1:]:
            union(members[0], other)
    roots = {find(i) for i in ids}
    return len(roots) == 1


def check_feasibility(
    graph: WeaveGraph,
    slots,
    *,
    max_unbound_fraction: float = 0.5,
    require_connected: bool = True,
) -> FeasibilityResult:
    reasons: list[str] = []

    bound = {n.bound_slot for n in graph.nodes if n.bound_slot}
    for slot in slots:
        if getattr(slot, "required", False) and slot.name not in bound:
            reasons.append(f"required slot '{slot.name}' unfilled")

    total = len(graph.nodes)
    if total:
        unbound = sum(1 for n in graph.nodes if not n.bound_slot)
        frac = unbound / total
        if frac > max_unbound_fraction:
            reasons.append(f"too many unbound (off-goal) paragraphs: {unbound}/{total} > {max_unbound_fraction:.0%}")

    if require_connected and not _connected(graph):
        reasons.append("entity graph is disconnected (no shared-entity path between some paragraphs)")

    return FeasibilityResult(ok=not reasons, reasons=reasons)
