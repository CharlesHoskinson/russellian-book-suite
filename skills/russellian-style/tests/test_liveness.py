"""Cites REQ-VEVAL-009. nPVI is the order-sensitive cadence signal that the Fano
factor cannot supply (Fano is permutation-invariant on sentence lengths)."""
import pytest

pytestmark = pytest.mark.windows_canary

from scripts.liveness import npvi, liveness_summary


def test_alternating_lengths_score_higher_than_uniform():
    uniform = " ".join([
        "This sentence carries exactly fourteen words and lands inside the suspect AI band cleanly.",
        "Another sentence of fifteen words again sits inside the same narrow predictable AI band.",
        "Yet another sentence of thirteen words drops squarely inside the AI signature band today.",
    ])
    alternating = " ".join([
        "A short opener arrives first.",
        "A much longer sentence follows, building up clauses, taking its time, reaching across many words before resolving on the final beat.",
        "Short again.",
        "And once more a long sentence stretches itself out, accumulating modifiers and weight, until it lands.",
    ])
    assert npvi(alternating) > npvi(uniform)


def test_single_qualifying_sentence_returns_zero():
    assert npvi("This is one sentence with more than four words.") == 0.0


def test_below_floor_fragments_are_ignored():
    # "Yes." / "No." stuffing must not inflate cadence: with the floor active, only
    # the two genuine sentences remain (equal length -> 0.0). With the floor disabled,
    # the fragments alternate with the long sentences and inflate the score above 0.
    text = " ".join([
        "Yes.", "No.", "Indeed.",
        "A genuine sentence with comfortably more than four words to clear the floor here.",
        "Another genuine sentence with comfortably more than four words to clear the floor again.",
    ])
    assert npvi(text) == 0.0
    assert npvi(text, min_words=1) > 0.0


def test_determinism():
    text = "A short sentence here. A markedly longer one trailing across more words to vary the cadence."
    assert npvi(text) == npvi(text)


def test_summary_keys_and_advisory_flag():
    s = liveness_summary(npvi_value=60.0, motion_variety=0.5,
                         concrete_per_1000=4.0, ornament_per_1000=0.0)
    assert s["metric"] == "liveness"
    assert s["advisory"] is True
    assert set(s["components"]) == {"cadence", "motion", "concreteness", "ornament_penalty"}
    assert 0.0 <= s["liveness"] <= 1.0


def test_more_ornament_lowers_liveness():
    base = liveness_summary(60.0, 0.5, 4.0, ornament_per_1000=0.0)["liveness"]
    pen = liveness_summary(60.0, 0.5, 4.0, ornament_per_1000=10.0)["liveness"]
    assert pen < base


def test_higher_npvi_raises_cadence_component():
    low = liveness_summary(10.0, 0.5, 4.0, 0.0)["components"]["cadence"]
    high = liveness_summary(80.0, 0.5, 4.0, 0.0)["components"]["cadence"]
    assert high > low


def test_liveness_floored_at_zero():
    s = liveness_summary(0.0, 0.0, 0.0, ornament_per_1000=999.0)
    assert s["liveness"] == 0.0


def test_summary_deterministic():
    args = dict(npvi_value=55.0, motion_variety=0.4, concrete_per_1000=3.0, ornament_per_1000=1.0)
    assert liveness_summary(**args) == liveness_summary(**args)
