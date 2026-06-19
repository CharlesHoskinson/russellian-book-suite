"""Cites REQ-VOICE-009, REQ-VOICE-010 (device-challenge: the real sample passes v2)."""
import pytest
pytestmark = pytest.mark.windows_canary
from pathlib import Path
from scripts.lint_common import load_rules
from scripts.lint_sentence_rhythm import lint_sentence_rhythm

SAMPLE = Path(__file__).resolve().parents[3] / "examples" / "triadic-trust-decomposition.md"


def test_sample_drumbeat_paragraph_passes_under_v2():
    # The trust-decomposition sample's first draft anaphora is a drumbeat, not a tic.
    # Under v2 it must not be flagged as rhythm-repeated-opening.
    assert SAMPLE.exists(), f"sample missing at {SAMPLE}"
    rules = load_rules("russellian-rules-v2.json")
    findings = lint_sentence_rhythm(SAMPLE, rules=rules)
    assert not any(f["rule"] == "rhythm-repeated-opening" for f in findings)
