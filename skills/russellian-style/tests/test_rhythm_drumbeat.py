"""Cites REQ-VOICE-009 (drumbeat exemption; v1 unchanged)."""
import pytest
pytestmark = pytest.mark.windows_canary
from pathlib import Path
from scripts.lint_common import load_rules
from scripts.lint_sentence_rhythm import lint_sentence_rhythm

DRUMBEAT = (
    "The setup ceremony that builds the mathematical stage is one trust. "
    "The language you wrote the program in is another. "
    "The witness, the arithmetization, the proof system, and the on-chain contract are each a separate bet. "
    "The verifier itself carries assumptions no one audited. "
    "What people miss is that every one of them is independently testable."
)
TIC = "This is fine. This is good. This is great. This is done."


def _write(tmp_path, text):
    p = tmp_path / "p.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_v1_still_flags_the_drumbeat(tmp_path):
    # frozen v1 behavior: the four "The" run is a repeated-opening defect
    findings = lint_sentence_rhythm(_write(tmp_path, DRUMBEAT))
    assert any(f["rule"] == "rhythm-repeated-opening" for f in findings)


def test_v2_exempts_the_drumbeat_as_parallel_list(tmp_path):
    rules = load_rules("russellian-rules-v2.json")
    findings = lint_sentence_rhythm(_write(tmp_path, DRUMBEAT), rules=rules)
    assert not any(f["rule"] == "rhythm-repeated-opening" for f in findings)
    assert any(f["rule"] == "parallel-list" for f in findings)


def test_v2_still_flags_a_real_tic(tmp_path):
    rules = load_rules("russellian-rules-v2.json")
    findings = lint_sentence_rhythm(_write(tmp_path, TIC), rules=rules)
    assert any(f["rule"] == "rhythm-repeated-opening" for f in findings)
