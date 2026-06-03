import pytest
pytestmark = pytest.mark.windows_canary

from scripts.system_prompt_loader import load_system_prompt, available_modes


def test_three_modes_available():
    modes = set(available_modes())
    assert {"technical-exposition", "pedagogical-walkthrough", "popular-science"} <= modes

def test_prompt_states_two_layer_contract():
    text = load_system_prompt("technical-exposition")
    assert "argument" in text.lower()
    assert "analogy" in text.lower()
