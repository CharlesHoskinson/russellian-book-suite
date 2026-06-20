"""Cites REQ-LIVE-003 (subject-verb distance; Gopen-Swan cognitive load)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.signal_sv_distance import score_text


@pytest.mark.needs_model
def test_tight_subject_verb_scores_high():
    out = score_text("The reader tracks the cue. You trust the bank.")
    assert out["score"] == 1.0
    assert not out["findings"]


@pytest.mark.needs_model
def test_far_separated_subject_verb_is_flagged():
    text = "The reader, who had spent the entire long and difficult afternoon rereading every footnote, paused."
    out = score_text(text)
    assert any(f["distance"] > 7 for f in out["findings"])
