import pytest
pytestmark = pytest.mark.windows_canary

from scripts.score_feynman_delta import score_text


def test_score_returns_float():
    score = score_text("atoms jiggle and bounce around like little balls")
    assert isinstance(score, float)
    assert score >= 0.0

def test_empty_text_scores_zero_or_nonnegative():
    assert score_text("") >= 0.0
