# skills/voice-eval/tests/test_human_study.py
"""Cites REQ-VEVAL-016, REQ-VEVAL-017 (human-study scaffold + graduation gate)."""
import pytest

pytestmark = pytest.mark.windows_canary

RUBRIC_DIMS = ("momentum", "clarity", "voice_authority", "readability", "trustworthiness")


def test_scaffold_min_items_and_randomized_blind():
    from scripts.human_study import build_study
    pairs = [{"prompt_id": f"X{i}", "v1": "a", "v2": "b"} for i in range(60)]
    study = build_study(pairs, seed=7, rubric=RUBRIC_DIMS)
    assert len(study["items"]) >= 50
    # Blind: each item presents A/B with the arm hidden behind a recoverable key.
    assert all(set(it["sides"]) == {"A", "B"} for it in study["items"])
    assert all("arm" not in it["sides"]["A"] for it in study["items"])
    assert set(study["rubric"]) == set(RUBRIC_DIMS)


def test_fleiss_kappa_perfect_agreement():
    from scripts.human_study import fleiss_kappa
    # 3 raters, 2 items, both unanimous → kappa 1.0
    # table[item] = {category: count}
    table = [{"A": 3, "B": 0}, {"A": 0, "B": 3}]
    assert round(fleiss_kappa(table), 6) == 1.0


def test_graduation_denied_without_ci_excluding_zero():
    from scripts.human_study import graduate
    # correlation present but CI straddles zero → denied
    g = graduate(spearman=0.55, ci=(-0.1, 0.8), trust_delta=0.0)
    assert g["graduates"] is False
    assert g["reasons"]["ci_excludes_zero"] is False


def test_graduation_denied_if_trust_degrades():
    from scripts.human_study import graduate
    g = graduate(spearman=0.7, ci=(0.4, 0.85), trust_delta=-0.02)
    assert g["graduates"] is False
    assert g["reasons"]["trust_not_degraded"] is False


def test_graduation_allowed_when_all_conditions_met():
    from scripts.human_study import graduate
    g = graduate(spearman=0.65, ci=(0.3, 0.82), trust_delta=0.01)
    assert g["graduates"] is True
