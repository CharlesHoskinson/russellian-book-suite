"""Cites REQ-LIVE-001, REQ-LIVE-002 (committed profile asset)."""
import pytest
pytestmark = pytest.mark.windows_canary
import skill_api


def test_committed_profile_has_all_registers():
    p = skill_api.load_profile()
    assert set(p["registers"]) == {"technical-exposition", "narrative-editorial", "polemic"}
    assert "no source prose" in p["source_policy"].lower()
    for reg in p["registers"].values():
        assert set(reg["cadence"]) >= {"p10", "p50", "p90", "cv", "count"}
