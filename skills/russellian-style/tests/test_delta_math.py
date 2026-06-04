"""Cites REQ-DELTA-003."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.delta_math import tokenize, relative_frequencies, cosine, cosine_delta, zscore, manhattan_delta


def test_tokenize_lowercases_and_splits():
    assert tokenize("The CAT's hat, and 3 dogs!") == ["the", "cat's", "hat", "and", "dogs"]

def test_relative_frequencies_align_to_mfw():
    toks = ["the", "of", "the", "cat"]
    assert relative_frequencies(toks, ["the", "of", "dog"]) == [0.5, 0.25, 0.0]

def test_relative_frequencies_empty_is_zeros():
    assert relative_frequencies([], ["the", "of"]) == [0.0, 0.0]

def test_cosine_orthogonal_is_zero():
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0

def test_cosine_parallel_is_one():
    assert cosine([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]) == pytest.approx(1.0)

def test_cosine_delta_is_one_minus_cosine():
    assert cosine_delta([1.0, 0.0], [0.0, 1.0]) == pytest.approx(1.0)
    assert cosine_delta([1.0, 1.0], [1.0, 1.0]) == pytest.approx(0.0)

def test_cosine_zero_vector_returns_zero():
    assert cosine([0.0, 0.0], [1.0, 1.0]) == 0.0

def test_zscore_uses_mean_and_stdev_with_zero_guard():
    assert zscore([0.6, 0.1], [0.5, 0.1], [0.1, 0.0]) == [pytest.approx(1.0), 0.0]

def test_manhattan_delta_is_mean_absolute_z():
    assert manhattan_delta([1.0, -1.0, 2.0]) == pytest.approx(4.0 / 3.0)
    assert manhattan_delta([]) == 0.0
