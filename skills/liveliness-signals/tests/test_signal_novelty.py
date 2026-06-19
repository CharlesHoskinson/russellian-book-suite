"""Cites REQ-LIVE-010 (novelty-continuity corridor; anti-gaming coherence)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.text_util import iter_sentences
from scripts.signal_novelty import score


@pytest.mark.needs_model
def test_restatement_is_flagged():
    text = "The proof hides the secret value. The proof hides the secret value entirely."
    out = score(iter_sentences(text), "narrative-editorial", None)
    assert any(f["flag"] == "restatement" for f in out["findings"])


@pytest.mark.needs_model
def test_disconnected_punchline_is_flagged_as_jump_cut():
    text = "The setup ceremony builds the mathematical stage carefully. Bananas ripen fastest in warm rooms."
    out = score(iter_sentences(text), "narrative-editorial", None)
    assert any(f["flag"] == "jump_cut" for f in out["findings"])
