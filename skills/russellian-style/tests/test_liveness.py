"""Cites REQ-VEVAL-009. nPVI is the order-sensitive cadence signal that the Fano
factor cannot supply (Fano is permutation-invariant on sentence lengths)."""
import pytest

pytestmark = pytest.mark.windows_canary

from scripts.liveness import npvi


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
    # "Yes." / "No." stuffing must not inflate cadence; the floor (default 4) drops them.
    text = " ".join([
        "Yes.", "No.", "Indeed.",
        "A genuine sentence with comfortably more than four words to clear the floor here.",
        "Another genuine sentence with comfortably more than four words to clear the floor again.",
    ])
    assert npvi(text) == 0.0  # only 2 qualifying sentences of similar length -> low contrast


def test_determinism():
    text = "A short sentence here. A markedly longer one trailing across more words to vary the cadence."
    assert npvi(text) == npvi(text)
