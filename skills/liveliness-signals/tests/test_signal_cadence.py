"""Cites REQ-LIVE-005 (cadence corridor, two-sided)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.text_util import iter_sentences
from scripts.signal_cadence import score

PROFILE = {"registers": {"narrative-editorial": {"cadence": {"cv": 0.5}}}}


@pytest.mark.needs_model
def test_metronomic_is_flagged():
    # five sentences of identical length -> cv ~ 0 -> metronomic
    text = " ".join(["The grey cat sat there quietly."] * 5)
    out = score(iter_sentences(text), "narrative-editorial", PROFILE)
    assert out["signal"] == "cadence"
    assert any(f["flag"] == "metronomic" for f in out["findings"])


@pytest.mark.needs_model
def test_varied_passage_scores_positive():
    text = ("No. " "The setup ceremony that builds the whole mathematical stage is the first trust you make. "
            "You check it. " "Then the language, the witness, and the proof all add their own separate bets.")
    out = score(iter_sentences(text), "narrative-editorial", PROFILE)
    assert out["score"] > 0.0
    assert not any(f["flag"] == "metronomic" for f in out["findings"])
