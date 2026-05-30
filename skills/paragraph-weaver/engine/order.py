"""Ordering search.

Exactly one HARD constraint: validated-acyclic precedence (src before dst). The
target's order_objective supplies SOFT penalties (slot order, edge-loading). At
demo scale (<= max_exact nodes) we enumerate every linear extension of the
precedence DAG and pick the objective-minimizing one. Above that we fall back to
one deterministic topological order to stay tractable.

Precondition: the graph's precedence edges are acyclic (callers run
engine.cycles.find_cycles first and resolve cycles). A cyclic graph yields no
topological order and raises ValueError.
"""
from __future__ import annotations

from typing import Callable

from engine.graph import Edge, WeaveGraph


def all_topological_orders(node_ids: list[str], edges: list[Edge]) -> list[list[str]]:
    preds: dict[str, set[str]] = {n: set() for n in node_ids}
    for e in edges:
        if e.kind == "precedence" and e.src != e.dst:
            preds.setdefault(e.dst, set()).add(e.src)
            preds.setdefault(e.src, set())
    results: list[list[str]] = []

    def backtrack(order: list[str], remaining: set[str]) -> None:
        if not remaining:
            results.append(list(order))
            return
        placed = set(order)
        for n in sorted(remaining):
            if preds.get(n, set()) <= placed:
                order.append(n)
                backtrack(order, remaining - {n})
                order.pop()

    backtrack([], set(node_ids))
    return results


def _single_topo_order(node_ids: list[str], edges: list[Edge]) -> list[str]:
    preds: dict[str, set[str]] = {n: set() for n in node_ids}
    for e in edges:
        if e.kind == "precedence" and e.src != e.dst:
            preds.setdefault(e.dst, set()).add(e.src)
            preds.setdefault(e.src, set())
    order: list[str] = []
    remaining = set(node_ids)
    while remaining:
        ready = sorted(n for n in remaining if preds.get(n, set()) <= set(order))
        if not ready:
            raise ValueError("precedence edges are cyclic; resolve cycles before ordering")
        order.append(ready[0])
        remaining.discard(ready[0])
    return order


def order_paragraphs(
    graph: WeaveGraph,
    objective: Callable[[list[str]], float],
    *,
    max_exact: int = 9,
) -> list[str]:
    node_ids = [n.id for n in graph.nodes]
    if len(node_ids) <= max_exact:
        orders = all_topological_orders(node_ids, graph.edges)
        if not orders:
            raise ValueError("precedence edges are cyclic; resolve cycles before ordering")
        return min(orders, key=objective)
    return _single_topo_order(node_ids, graph.edges)
