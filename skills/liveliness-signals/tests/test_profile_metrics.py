"""Cites REQ-LIVE-001, REQ-LIVE-005 (cadence corridor stats)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.profile_metrics import sentence_lengths, cadence_corridor


@pytest.mark.needs_model
def test_sentence_lengths_counts_word_tokens():
    lens = sentence_lengths(["One two three. Four five."])
    assert lens == [3, 2]


def test_cadence_corridor_shape_and_cv():
    c = cadence_corridor([2, 4, 4, 6, 8])
    assert set(c) == {"p10", "p25", "p50", "p75", "p90", "cv", "count"}
    assert c["count"] == 5
    assert c["p50"] == 4
    assert c["cv"] > 0


def test_cadence_corridor_empty_is_safe():
    c = cadence_corridor([])
    assert c["count"] == 0 and c["cv"] == 0.0
