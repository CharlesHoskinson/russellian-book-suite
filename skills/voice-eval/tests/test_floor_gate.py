# skills/voice-eval/tests/test_floor_gate.py
"""Cites REQ-VEVAL-010 (equal-grounding v1 floor gate)."""
import pytest

pytestmark = pytest.mark.windows_canary


def _fake_battery(passing_ids):
    # Returns total floor-violation count: 0 for passing passages, else 3.
    def battery(text, prompt_id, arm):
        return 0 if (prompt_id, arm) in passing_ids else 3
    return battery


def test_gate_flags_failures_for_regeneration():
    from scripts.floor_gate import gate_passages
    passages = [
        {"prompt_id": "T01", "arm": "v1", "register": "technical-exposition", "text": "a"},
        {"prompt_id": "T01", "arm": "v2", "register": "technical-exposition", "text": "b"},
    ]
    passing = {("T01", "v1")}              # v2 fails the floor
    result = gate_passages(passages, battery=_fake_battery(passing))
    assert result["all_clean"] is False
    assert [(f["prompt_id"], f["arm"]) for f in result["failures"]] == [("T01", "v2")]


def test_gate_all_clean_when_zero_violations():
    from scripts.floor_gate import gate_passages
    passages = [{"prompt_id": "T01", "arm": "v1", "register": "technical-exposition", "text": "a"}]
    result = gate_passages(passages, battery=_fake_battery({("T01", "v1")}))
    assert result["all_clean"] is True
    assert result["failures"] == []
