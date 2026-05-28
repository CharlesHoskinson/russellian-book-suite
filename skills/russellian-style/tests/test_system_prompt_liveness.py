"""Cites REQ-VOICE-008 through REQ-VOICE-012, REQ-VOICE-017.

Each mode prompt's # Calibration and planning section must contain a ## Liveness
subsection at the declared intensity for that mode, with at least one anchor
referencing a longfellow-corpus snippet ID, and the firewall stated.
"""
import json
import pytest

pytestmark = pytest.mark.windows_canary

from scripts.system_prompt_loader import load, VALID_MODES, PROMPTS_DIR


MODE_DIAL = {
    "technical-exposition": "low",
    "narrative-editorial": "high",
    "polemic": "medium",
}

assert set(MODE_DIAL) == VALID_MODES, (
    f"MODE_DIAL keys {sorted(MODE_DIAL)} must match VALID_MODES {sorted(VALID_MODES)}"
)

CORPUS_INDEX = (PROMPTS_DIR.parent / "longfellow-corpus" / "index.json")

ANCHOR_IDS = {a["id"] for a in json.loads(CORPUS_INDEX.read_text(encoding="utf-8"))["anchors"]}


@pytest.mark.parametrize("mode", sorted(VALID_MODES))
def test_each_mode_has_liveness_subsection_at_declared_dial(mode):
    text = load(mode)
    assert "## Liveness" in text, f"{mode} missing ## Liveness subsection"
    dial = MODE_DIAL[mode]
    # Intensity declared in plain prose: "Intensity: low" / "Intensity: high" / "Intensity: medium"
    assert f"Intensity: {dial}" in text, f"{mode} ## Liveness section must declare 'Intensity: {dial}'"


@pytest.mark.parametrize("mode", sorted(VALID_MODES))
def test_each_mode_cites_a_longfellow_corpus_anchor(mode):
    text = load(mode)
    assert any(aid in text for aid in ANCHOR_IDS), (
        f"{mode} ## Liveness section must reference at least one anchor ID from "
        f"longfellow-corpus/index.json"
    )


@pytest.mark.parametrize("mode", sorted(VALID_MODES))
def test_each_mode_states_the_firewall(mode):
    text = load(mode)
    assert "never meter" in text.lower(), (
        f"{mode} ## Liveness section must state the firewall (e.g., "
        f"'borrow cadence and image-logic only, never meter, rhyme, archaism, or sentiment')"
    )
