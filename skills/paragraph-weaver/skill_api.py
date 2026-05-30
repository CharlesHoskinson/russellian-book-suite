# skill_api.py
"""Public surface for paragraph-weaver.

Importing this module registers the three v1 targets and re-exports the
deterministic engine functions. The agent that runs the skill (see SKILL.md)
calls these to assemble, validate, order, and gate a thread; it supplies the
generative inputs (goal-spec, role tags, precedence edges, bridges, seam edits).
"""
from __future__ import annotations

API_VERSION = (0, 1)

# Register targets (import side effects populate the registry).
import targets.argument  # noqa: F401,E402
import targets.emotion  # noqa: F401,E402
import targets.narrative  # noqa: F401,E402

from targets.base import REGISTRY, Slot, GateResult, Target, get_target, register  # noqa: E402
from engine.graph import Node, Edge, WeaveGraph  # noqa: E402
from engine.cycles import find_cycles  # noqa: E402
from engine.feasibility import check_feasibility, FeasibilityResult  # noqa: E402
from engine.order import order_paragraphs, all_topological_orders  # noqa: E402
from engine.weave import (  # noqa: E402
    validate_bridge, validate_seam_edit, load_relations,
    BridgeValidation, SeamValidation,
)
from engine.gate import no_silent_drops, bridge_load_ratio, score_gate  # noqa: E402
from engine.report import Segment, render_provenance, render_clean  # noqa: E402
from scripts.features import extract_entities  # noqa: E402

__all__ = [
    "API_VERSION",
    "REGISTRY", "Slot", "GateResult", "Target", "get_target", "register",
    "Node", "Edge", "WeaveGraph",
    "find_cycles",
    "check_feasibility", "FeasibilityResult",
    "order_paragraphs", "all_topological_orders",
    "validate_bridge", "validate_seam_edit", "load_relations",
    "BridgeValidation", "SeamValidation",
    "no_silent_drops", "bridge_load_ratio", "score_gate",
    "Segment", "render_provenance", "render_clean",
    "extract_entities",
]
