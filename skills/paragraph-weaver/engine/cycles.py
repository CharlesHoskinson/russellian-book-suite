# engine/cycles.py
"""Tarjan strongly-connected-components cycle detection over precedence edges.

A precedence edge (src -> dst) means src must appear before dst. Any SCC with
more than one node, or any self-loop, is a cycle that makes the precedence
constraint set infeasible. Per the spec, the engine REPORTS cycles for
adjudication rather than crashing; callers demote the weakest edge in the SCC.
"""
from __future__ import annotations

from engine.graph import WeaveGraph


def find_cycles(graph: WeaveGraph) -> list[list[str]]:
    adj: dict[str, list[str]] = {n.id: [] for n in graph.nodes}
    self_loops: list[str] = []
    for e in graph.edges:
        if e.kind != "precedence":
            continue
        if e.src == e.dst:
            self_loops.append(e.src)
            continue
        adj.setdefault(e.src, []).append(e.dst)
        adj.setdefault(e.dst, [])

    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: dict[str, bool] = {}
    stack: list[str] = []
    counter = [0]
    cycles: list[list[str]] = []

    def strongconnect(v: str) -> None:
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack[v] = True
        for w in adj.get(v, []):
            if w not in index:
                strongconnect(w)
                low[v] = min(low[v], low[w])
            elif on_stack.get(w):
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                cycles.append(sorted(comp))

    for n in graph.nodes:
        if n.id not in index:
            strongconnect(n.id)

    for node_id in self_loops:
        cycles.append([node_id])
    return cycles
