"""Cites REQ-VEVAL-001, REQ-VEVAL-002, REQ-VEVAL-008."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.voice_eval import build_generation_prompt, generate_paragraphs, DEFAULT_N


def test_default_paragraph_count_is_30():
    assert DEFAULT_N == 30

def test_prompt_embeds_contract_topic_and_count():
    p = build_generation_prompt("the history of zero", "polemic", 12)
    assert "the history of zero" in p
    assert "12" in p
    assert "# Calibration and planning" in p
    assert "verdict" in p.lower() or "antithesis" in p.lower()

def test_generate_paragraphs_calls_llm_with_prompt_and_returns_output():
    captured = {}
    def fake_llm(prompt):
        captured["prompt"] = prompt
        return "GENERATED PROSE"
    out = generate_paragraphs("topic X", mode="technical-exposition", n=5, llm_call=fake_llm)
    assert out == "GENERATED PROSE"
    assert "topic X" in captured["prompt"]
    assert "5" in captured["prompt"]

def test_generate_paragraphs_rejects_unknown_mode():
    with pytest.raises(ValueError):
        generate_paragraphs("t", mode="nope", n=5, llm_call=lambda p: "")
