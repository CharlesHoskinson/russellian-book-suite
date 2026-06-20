# skills/voice-eval/tests/test_prompts.py
"""Cites REQ-VEVAL-009 (20-prompt stratified set)."""
import pytest

pytestmark = pytest.mark.windows_canary

REGISTERS = {"technical-exposition", "narrative-editorial", "polemic"}


def test_loads_exactly_twenty_unique_prompts():
    from scripts.prompts import load_prompts
    ps = load_prompts()
    assert len(ps) == 20
    ids = [p["id"] for p in ps]
    assert len(set(ids)) == 20
    assert all(p["topic"].strip() for p in ps)


def test_stratified_seven_seven_six():
    from scripts.prompts import load_prompts, register_counts
    counts = register_counts(load_prompts())
    assert counts == {"technical-exposition": 7, "narrative-editorial": 7, "polemic": 6}


def test_validate_rejects_bad_register():
    from scripts.prompts import validate_prompts, PromptSetError
    with pytest.raises(PromptSetError):
        validate_prompts([{"id": "x", "topic": "t", "register": "bogus"}])
