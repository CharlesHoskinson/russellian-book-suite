# skills/voice-eval/tests/test_ballot.py
"""Cites REQ-VEVAL-012 (blind, order-swapped, length-matched pairwise ballots)."""
import pytest

pytestmark = pytest.mark.windows_canary


def _pair(pid):
    return (
        {"prompt_id": pid, "arm": "v1", "register": "polemic", "text": "x " * 50},
        {"prompt_id": pid, "arm": "v2", "register": "polemic", "text": "y " * 50},
    )


def test_two_order_swapped_ballots_per_prompt():
    from scripts.ballot import build_ballots
    v1, v2 = _pair("P01")
    ballots = build_ballots([v1], [v2])
    assert len(ballots) == 2
    # The same pair appears with A/B assignment swapped.
    a_arms = {b["A"]["arm"] for b in ballots}
    assert a_arms == {"v1", "v2"}
    # Blind: the arm label is not leaked into the side payload shown to the judge.
    assert "arm" not in ballots[0]["A"]["shown"]


def test_length_match_flag_and_required_fields():
    from scripts.ballot import build_ballots, VERDICT_FIELDS
    v1, v2 = _pair("P01")
    ballots = build_ballots([v1], [v2])
    b = ballots[0]
    assert b["length_matched"] is True
    assert set(VERDICT_FIELDS) == {
        "keep", "want_next", "momentum", "clarity",
        "voice_authority", "readability", "trustworthiness", "rationale",
    }


def test_length_mismatch_detected():
    from scripts.ballot import build_ballots
    short = {"prompt_id": "P01", "arm": "v1", "register": "polemic", "text": "short"}
    long = {"prompt_id": "P01", "arm": "v2", "register": "polemic", "text": "w " * 200}
    ballots = build_ballots([short], [long])
    assert ballots[0]["length_matched"] is False
