"""Cites REQ-TRIAD-003 (profile-driven statistical targets)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.profile_targets import targets, as_prompt

PROFILE = {"registers": {"narrative-editorial": {
    "cadence": {"p10": 4.0, "p90": 28.0, "cv": 0.55},
    "diction": {"discourse_marker_rate": 0.2, "direct_address_rate": 0.3, "example_spacing": 3.0},
    "modifier": {"p90": 0.24}}}}


def test_targets_shape_and_values():
    t = targets("narrative-editorial", PROFILE)
    assert t["sentence_len_band"] == (4.0, 28.0)
    assert t["cadence_cv"] == 0.55
    assert 0.0 <= t["modifier_budget"] <= 1.0


def test_as_prompt_is_injectable_text():
    s = as_prompt(targets("narrative-editorial", PROFILE))
    assert "sentence length" in s.lower() and "4" in s and "28" in s
