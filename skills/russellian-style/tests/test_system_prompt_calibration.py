"""Calibration contract for mode system prompts.

Cites REQ-VOICE-001, REQ-VOICE-002, REQ-VOICE-003, REQ-VOICE-004, REQ-VOICE-007.
"""
import pytest

pytestmark = pytest.mark.windows_canary

from scripts.system_prompt_loader import load, VALID_MODES

MOTION_SEQUENCE = "concession → example → distinction → consequence → turn"


@pytest.mark.parametrize("mode", sorted(VALID_MODES))
def test_REQ_VOICE_001_calibration_heading_present(mode):
    assert "# Calibration and planning" in load(mode)


@pytest.mark.parametrize("mode", sorted(VALID_MODES))
def test_REQ_VOICE_002_planning_motion_sequence_present(mode):
    assert MOTION_SEQUENCE in load(mode)


@pytest.mark.parametrize("mode", sorted(VALID_MODES))
def test_REQ_VOICE_002_plan_is_not_emitted(mode):
    assert "not emit" in load(mode).lower()


@pytest.mark.parametrize("mode", sorted(VALID_MODES))
def test_REQ_VOICE_003_004_attributed_anchor_present(mode):
    text = load(mode)
    assert "russell-corpus-map.md" in text
    assert "gutenberg.org" in text
    assert "Touchstone" in text
