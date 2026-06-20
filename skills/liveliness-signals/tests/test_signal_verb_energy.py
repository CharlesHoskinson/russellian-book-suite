"""Cites REQ-LIVE-006 (verb-energy: lexical verbs + light-verb-construction flags)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.signal_verb_energy import score_text


@pytest.mark.needs_model
def test_action_prose_scores_higher_than_noun_pile():
    active = "She cuts the deck, breaks the seal, and hands you the card."
    nouny = "The verification of the transaction is a consideration for the formalization."
    assert score_text(active)["score"] > score_text(nouny)["score"]


@pytest.mark.needs_model
def test_light_verb_construction_is_flagged():
    out = score_text("The team will make a proposal about the migration.")
    assert any("make" in f.get("construction", "") for f in out["findings"])
