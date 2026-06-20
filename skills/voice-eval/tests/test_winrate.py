# skills/voice-eval/tests/test_winrate.py
"""Cites REQ-VEVAL-012 (win-rate with confidence interval)."""
import pytest

pytestmark = pytest.mark.windows_canary


def _filled(prompt_id, order, keep_arm, ballots_arms):
    # ballots_arms: which arm is 'A' in this ballot; keep is the letter that selects keep_arm
    keep_letter = "A" if ballots_arms["A"] == keep_arm else "B"
    return {
        "prompt_id": prompt_id, "order": order,
        "A": {"arm": ballots_arms["A"]}, "B": {"arm": ballots_arms["B"]},
        "verdict": {"keep": keep_letter},
    }


def test_winrate_counts_v2_keeps():
    from scripts.winrate import win_rate
    # Two prompts, both orders pick v2 → v2 win-rate 1.0
    ballots = [
        _filled("P01", 0, "v2", {"A": "v1", "B": "v2"}),
        _filled("P01", 1, "v2", {"A": "v2", "B": "v1"}),
        _filled("P02", 0, "v2", {"A": "v1", "B": "v2"}),
        _filled("P02", 1, "v2", {"A": "v2", "B": "v1"}),
    ]
    r = win_rate(ballots, target="v2")
    assert r["wins"] == 4 and r["n"] == 4
    assert r["rate"] == 1.0
    assert 0.0 <= r["ci_low"] <= r["ci_high"] <= 1.0
    assert r["ci_low"] > 0.4   # 4/4 lower Wilson bound well above chance


def test_wilson_interval_known_value():
    from scripts.winrate import wilson_interval
    lo, hi = wilson_interval(8, 10)   # 0.8 of 10
    assert round(lo, 3) == 0.490
    assert round(hi, 3) == 0.943
