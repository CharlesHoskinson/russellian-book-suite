"""Cites REQ-VOICE-009, REQ-VOICE-010 (device-challenge set; v1 unchanged).

Item 1 of the device-challenge set is the trust-decomposition sample's original
first-draft drumbeat — the four-clause "The ..." run that v1 wrongly flagged. v2
must exempt it as a parallel-list while v1 still flags it. A separate smoke check
confirms the shipped (hand-fixed) sample carries no v2 regression.
"""
import pytest
pytestmark = pytest.mark.windows_canary
from pathlib import Path
from scripts.lint_common import load_rules
from scripts.lint_sentence_rhythm import lint_sentence_rhythm

SAMPLE = Path(__file__).resolve().parents[3] / "examples" / "triadic-trust-decomposition.md"

# The sample's ORIGINAL first-draft drumbeat — the motivating false positive.
SAMPLE_DRUMBEAT = (
    "The setup ceremony that builds the mathematical stage is one trust. "
    "The language you wrote the program in is another. "
    "The witness, the arithmetization, the proof system, the hardness assumption underneath it, "
    "and the contract on chain that renders the verdict are each a separate bet. "
    "The part people miss is that every one of them is independently testable. "
    "You can break the ceremony without breaking the curve."
)


def _write(tmp_path, text):
    p = tmp_path / "p.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_sample_original_drumbeat_exempted_under_v2(tmp_path):
    rules = load_rules("russellian-rules-v2.json")
    findings = lint_sentence_rhythm(_write(tmp_path, SAMPLE_DRUMBEAT), rules=rules)
    assert not any(f["rule"] == "rhythm-repeated-opening" for f in findings)
    assert any(f["rule"] == "parallel-list" for f in findings)


def test_sample_original_drumbeat_flagged_under_v1(tmp_path):
    findings = lint_sentence_rhythm(_write(tmp_path, SAMPLE_DRUMBEAT))  # v1 default
    assert any(f["rule"] == "rhythm-repeated-opening" for f in findings)


def test_shipped_sample_has_no_v2_regression():
    # The shipped sample was hand-fixed (run broken), so this is a no-regression
    # smoke, not an exemption proof — the exemption is proven by the
    # original-drumbeat tests above.
    assert SAMPLE.exists(), f"sample missing at {SAMPLE}"
    rules = load_rules("russellian-rules-v2.json")
    findings = lint_sentence_rhythm(SAMPLE, rules=rules)
    assert not any(f["rule"] == "rhythm-repeated-opening" for f in findings)
