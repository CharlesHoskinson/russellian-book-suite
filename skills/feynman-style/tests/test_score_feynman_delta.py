import pytest
pytestmark = pytest.mark.windows_canary

from scripts.score_feynman_delta import score_text


def test_score_returns_float():
    score = score_text("atoms jiggle and bounce around like little balls")
    assert isinstance(score, float)
    assert score >= 0.0

def test_empty_text_scores_zero_or_nonnegative():
    assert score_text("") >= 0.0


def test_oov_padding_does_not_change_delta():
    """H-07: the sample is normalized over in-vocab tokens, so padding the text
    with out-of-vocabulary words must not move the delta. Known answer: a sample
    matching the profile exactly scores 0, with or without OOV padding."""
    profile = {"frequencies": {"atoms": 0.5, "jiggle": 0.5}}
    base = "atoms jiggle"
    padded = "atoms jiggle zzzz qqqq wxyz vvvv"   # 4 OOV tokens, none in vocab
    d_base = score_text(base, profile)
    d_padded = score_text(padded, profile)
    assert d_base == pytest.approx(0.0, abs=1e-9)
    assert d_padded == pytest.approx(d_base, abs=1e-9)
