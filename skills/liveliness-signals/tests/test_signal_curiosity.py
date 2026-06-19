"""Cites REQ-LIVE-008 (setup-payoff, not keywords). Fixes the curiosity-absent false positive."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.text_util import iter_sentences
from scripts.signal_curiosity import score

# The motivating sample text that the old keyword detector wrongly called "curiosity-absent".
SAMPLE = ("Here's why that matters. Think about what you do when a bank tells you your balance is correct. "
          "You trust the bank. What people miss is that every one of them is independently testable.")


@pytest.mark.needs_model
def test_sample_curiosity_is_detected():
    out = score(iter_sentences(SAMPLE), "narrative-editorial", None)
    assert out["signal"] == "curiosity"
    assert out["score"] > 0.0
    assert len(out["findings"]) >= 1


@pytest.mark.needs_model
def test_flat_definition_has_no_curiosity():
    out = score(iter_sentences("A commitment scheme hides a value. It binds the value. It opens later."), "technical-exposition", None)
    assert out["score"] == 0.0


@pytest.mark.needs_model
def test_setup_with_only_filler_payoff_does_not_score():
    # a setup cue followed only by a content-thin filler line is not a real pair
    out = score(iter_sentences("Here's why that matters. It just does."), "narrative-editorial", None)
    assert out["score"] == 0.0
