"""Cites REQ-VOICE-022, REQ-VOICE-023.

Filename test_chassis_judge.py. No spaCy. All tests use a stubbed dispatcher;
no live LLM call is ever made.
"""
import pytest

pytestmark = pytest.mark.windows_canary

from scripts.chassis_judge import (
    chassis_judge,
    _build_judge_prompt,
    _parse_judge_response,
)


_DOC = (
    "The snail crosses the flagstone.\n\n"
    "The shell records the seasons in calcium.\n\n"
    "We have built whole industries on what the snail does without thought."
)

_FAKE_RESPONSE = """\
PARAGRAPH_MOVES:
1. concrete-scene-opener
2. specific-fact
3. humanity-aphorism

MOVE_TAXONOMY:
- concrete-scene-opener
- specific-fact
- humanity-aphorism

MOST_FREQUENT_MOVE: humanity-aphorism
MOST_FREQUENT_MOVE_FREQUENCY: 0.33
SINGLE_MOVE_SUMMARY: no
UNSYMPATHETIC_CRITIQUE: The essay is too short to monotone, but ends on a generalising verdict.
"""


def test_build_judge_prompt_embeds_document_and_format():
    prompt = _build_judge_prompt(_DOC)
    assert _DOC in prompt
    assert "PARAGRAPH_MOVES:" in prompt
    assert "MOVE_TAXONOMY:" in prompt
    assert "MOST_FREQUENT_MOVE:" in prompt
    assert "MOST_FREQUENT_MOVE_FREQUENCY:" in prompt
    assert "SINGLE_MOVE_SUMMARY:" in prompt
    assert "UNSYMPATHETIC_CRITIQUE:" in prompt


def test_parse_judge_response_extracts_all_fields():
    result = _parse_judge_response(_FAKE_RESPONSE)
    assert result["paragraph_moves"] == [
        "concrete-scene-opener", "specific-fact", "humanity-aphorism",
    ]
    assert set(result["move_taxonomy"]) == {
        "concrete-scene-opener", "specific-fact", "humanity-aphorism",
    }
    assert result["most_frequent_move"] == "humanity-aphorism"
    assert result["most_frequent_move_frequency"] == pytest.approx(0.33)
    assert result["single_move_summary"] is False
    assert "generalising" in result["unsympathetic_critique"]


def test_parse_judge_response_single_move_yes():
    response = _FAKE_RESPONSE.replace("SINGLE_MOVE_SUMMARY: no", "SINGLE_MOVE_SUMMARY: yes")
    result = _parse_judge_response(response)
    assert result["single_move_summary"] is True


def test_chassis_judge_invokes_dispatcher_with_prompt_and_returns_parsed():
    captured = {}

    def fake_dispatcher(prompt: str) -> str:
        captured["prompt"] = prompt
        return _FAKE_RESPONSE

    result = chassis_judge(_DOC, dispatcher=fake_dispatcher)
    assert _DOC in captured["prompt"]
    assert result["metric"] == "chassis-judge"
    assert result["advisory"] is True
    assert result["most_frequent_move"] == "humanity-aphorism"
    assert result["most_frequent_move_frequency"] == pytest.approx(0.33)
    assert isinstance(result["paragraph_moves"], list)
    assert isinstance(result["unsympathetic_critique"], str)


def test_chassis_judge_does_not_call_dispatcher_more_than_once():
    call_count = {"n": 0}

    def fake_dispatcher(prompt: str) -> str:
        call_count["n"] += 1
        return _FAKE_RESPONSE

    chassis_judge(_DOC, dispatcher=fake_dispatcher)
    assert call_count["n"] == 1


def test_frequency_clamped_into_unit_interval():
    # REQ-VOICE-022: frequency is a fraction in 0..1. A malformed dispatcher value
    # must not leak out of range (it would otherwise distort the Condition-1 check).
    over = _FAKE_RESPONSE.replace(
        "MOST_FREQUENT_MOVE_FREQUENCY: 0.33", "MOST_FREQUENT_MOVE_FREQUENCY: 1.7"
    )
    under = _FAKE_RESPONSE.replace(
        "MOST_FREQUENT_MOVE_FREQUENCY: 0.33", "MOST_FREQUENT_MOVE_FREQUENCY: -0.4"
    )
    assert _parse_judge_response(over)["most_frequent_move_frequency"] == 1.0
    assert _parse_judge_response(under)["most_frequent_move_frequency"] == 0.0


def test_chassis_judge_return_keys():
    result = chassis_judge(_DOC, dispatcher=lambda p: _FAKE_RESPONSE)
    assert set(result.keys()) == {
        "metric",
        "paragraph_moves",
        "move_taxonomy",
        "most_frequent_move",
        "most_frequent_move_frequency",
        "single_move_summary",
        "unsympathetic_critique",
        "advisory",
    }
