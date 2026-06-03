# tests/test_end_to_end.py
"""End-to-end: thread five argument paragraphs (snail-essay shape) toward a thesis.

The roles/slots/edges/bridge below stand in for the agent's judged outputs so the
deterministic pipeline can be exercised reproducibly. The paragraph texts share
the spine word "snail" so the entity graph is connected (a coherent argument's
paragraphs share vocabulary), which is what check_feasibility requires.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

import skill_api as api


def _build_graph():
    paras = [
        ("p_thesis", "The snail rewards exact attention.", "claim", "thesis"),
        ("p_shell", "The snail shell is a logarithmic spiral set by a single gene.", "premise", "evidence"),
        ("p_mucus", "The snail slime is glue and lubricant at once, and costly to make.", "premise", "evidence"),
        ("p_concession", "The snail looks simple and slow.", "rebuttal", "concession"),
        ("p_close", "Nothing in nature is humble except our knowledge of the snail.", "conclusion", "conclusion"),
    ]
    nodes = [
        api.Node(id=i, text=t, entities=api.extract_entities(t), role=r, bound_slot=s)
        for (i, t, r, s) in paras
    ]
    # Precedence: thesis before its evidence; evidence and concession before the close.
    edges = [
        api.Edge(src="p_thesis", dst="p_shell"),
        api.Edge(src="p_thesis", dst="p_mucus"),
        api.Edge(src="p_shell", dst="p_close"),
        api.Edge(src="p_mucus", dst="p_close"),
        api.Edge(src="p_concession", dst="p_close"),
    ]
    return api.WeaveGraph(nodes=nodes, edges=edges)


def test_pipeline_threads_all_paragraphs_and_passes_gate():
    target = api.get_target("argument")
    goal = {"thesis": "The snail rewards exact attention."}
    graph = _build_graph()

    # 1. No cycles.
    assert api.find_cycles(graph) == []

    # 2. Feasible (entity graph connected via the shared "snail" spine).
    feasible = api.check_feasibility(graph, target.plan_template(goal))
    assert feasible.ok, feasible.reasons

    # 3. Order (hard precedence + soft dispositio objective).
    order = api.order_paragraphs(graph, lambda seq: target.order_objective(seq, graph, goal))
    assert order[0] == "p_thesis"
    assert order.index("p_shell") < order.index("p_close")
    assert order[-1] == "p_close"

    # 4. One validated bridge after the thesis. It reuses only flanking vocabulary:
    #    "snail" is in every paragraph; "rewards"/"attention" are in the thesis.
    left = graph.node(order[0])
    right = graph.node(order[1])
    bridge_text = "This snail rewards attention."
    assert set(api.extract_entities(bridge_text)) <= set(left.entities) | set(right.entities)
    bridge = api.validate_bridge(
        bridge_text, left.entities, right.entities, relation="evidence-of"
    )
    assert bridge.ok, bridge.reasons

    # 5. Assemble segments in order, inserting the bridge after the thesis.
    segments = []
    for pos, nid in enumerate(order):
        segments.append(api.Segment(kind="source", text=graph.node(nid).text))
        if pos == 0:
            segments.append(api.Segment(kind="bridge", text=bridge_text))
    marked = api.render_provenance(segments)
    assert "<!-- bridge -->" in marked

    # 6. Gate over frozen artifacts.
    source_chars = sum(len(graph.node(nid).text) for nid in order)
    artifacts = {
        "input_ids": [n.id for n in graph.nodes],
        "output_ids": order,
        "source_chars": source_chars,
        "bridge_chars": len(bridge_text),
        "bridge_validity": [bridge.ok],
    }
    result = target.gate_hook(artifacts)
    assert result.passed, result.notes
    assert result.mechanical["no_silent_drops"] is True
