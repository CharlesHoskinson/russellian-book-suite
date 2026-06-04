# tests/test_gate.py
from __future__ import annotations

import pytest
pytestmark = pytest.mark.windows_canary

from engine.gate import no_silent_drops, bridge_load_ratio, score_gate


def test_no_silent_drops_detects_missing():
    ok, reasons = no_silent_drops(["a", "b", "c"], ["a", "b"])
    assert not ok
    assert any("c" in r for r in reasons)


def test_no_silent_drops_passes_on_equal_sets():
    ok, reasons = no_silent_drops(["a", "b"], ["b", "a"])
    assert ok and reasons == []


def test_bridge_load_ratio():
    assert bridge_load_ratio(900, 100) == 0.1


def test_score_gate_passes_clean_artifacts():
    artifacts = {
        "input_ids": ["a", "b"],
        "output_ids": ["a", "b"],
        "source_chars": 900,
        "bridge_chars": 100,
        "bridge_validity": [True, True],
    }
    res = score_gate(artifacts)
    assert res.passed
    assert res.mechanical["no_silent_drops"] is True


def test_score_gate_fails_on_drop_and_overload():
    artifacts = {
        "input_ids": ["a", "b", "c"],
        "output_ids": ["a"],
        "source_chars": 100,
        "bridge_chars": 900,
        "bridge_validity": [False],
    }
    res = score_gate(artifacts)
    assert not res.passed
    assert res.mechanical["bridge_load_ok"] is False


def test_score_gate_is_deterministic():
    artifacts = {
        "input_ids": ["a"],
        "output_ids": ["a"],
        "source_chars": 50,
        "bridge_chars": 0,
        "bridge_validity": [],
    }
    a = score_gate(artifacts)
    b = score_gate(artifacts)
    assert (a.passed, a.mechanical, a.notes) == (b.passed, b.mechanical, b.notes)
