# tests/test_stubs.py
from __future__ import annotations

import pytest
pytestmark = pytest.mark.windows_canary

from engine.graph import WeaveGraph
from targets.emotion import EmotionTarget
from targets.narrative import NarrativeTarget


def test_emotion_is_shallow_and_warns():
    t = EmotionTarget()
    assert t.depth == "shallow"
    res = t.gate_hook({})
    assert res.passed is True
    assert any("SHALLOW" in n for n in res.notes)


def test_narrative_is_shallow_and_warns():
    t = NarrativeTarget()
    assert t.depth == "shallow"
    res = t.gate_hook({})
    assert any("SHALLOW" in n for n in res.notes)


def test_stub_order_objective_is_trivial():
    t = EmotionTarget()
    assert t.order_objective(["x", "y"], WeaveGraph(nodes=[]), {}) == 0.0
