# skills/voice-eval/tests/test_report.py
"""Cites REQ-VEVAL-015 (success criterion + report)."""
import pytest

pytestmark = pytest.mark.windows_canary


def _good():
    return {
        "floor": {"all_clean": True, "failures": []},
        "deltas": {"overall": {"cadence": 0.2, "verb_energy": 0.1}, "per_register": {}},
        "winrate": {"target": "v2", "rate": 0.65, "n": 40, "ci_low": 0.5, "ci_high": 0.78},
        "trust": {"v2_minus_v1": 0.1},
        "drift": {"v1_mean_cosine": 0.7, "v2_mean_cosine": 0.5},
    }


def test_success_when_all_criteria_met():
    from scripts.report import evaluate_success
    v = evaluate_success(**_good())
    assert v["passed"] is True
    assert all(v["criteria"].values())


def test_fail_when_v2_loses_pairwise():
    from scripts.report import evaluate_success
    g = _good(); g["winrate"]["rate"] = 0.45
    v = evaluate_success(**g)
    assert v["passed"] is False
    assert v["criteria"]["wins_majority"] is False


def test_fail_when_trustworthiness_worse():
    from scripts.report import evaluate_success
    g = _good(); g["trust"]["v2_minus_v1"] = -0.05
    v = evaluate_success(**g)
    assert v["passed"] is False
    assert v["criteria"]["trust_not_worse"] is False


def test_report_renders_markdown(tmp_path):
    from scripts.report import evaluate_success, render_report
    v = evaluate_success(**_good())
    out = tmp_path / "r.md"
    render_report(v, _good(), out)
    text = out.read_text(encoding="utf-8")
    assert "# HFR v2 — 20×20 report" in text
    assert "PASS" in text
