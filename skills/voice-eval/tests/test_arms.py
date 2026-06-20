# skills/voice-eval/tests/test_arms.py
"""Cites REQ-VEVAL-009 (v1+v2 generation → 40 passages)."""
import pytest

pytestmark = pytest.mark.windows_canary


def _stub(arm):
    # Deterministic generator: echoes arm + prompt id so passages are distinguishable.
    def gen(prompt):
        return f"[{arm}] {prompt['topic']} ({prompt['register']})."
    return gen


def test_run_arms_produces_forty_tagged_passages():
    from scripts.prompts import load_prompts
    from scripts.arms import run_arms
    passages = run_arms(load_prompts(), generate_v1=_stub("v1"), generate_v2=_stub("v2"))
    assert len(passages) == 40
    arms = {p["arm"] for p in passages}
    assert arms == {"v1", "v2"}
    # Every prompt appears once per arm, register carried through.
    pairs = {(p["prompt_id"], p["arm"]) for p in passages}
    assert len(pairs) == 40
    assert all(p["register"] in {"technical-exposition", "narrative-editorial", "polemic"} for p in passages)


def test_run_arms_records_text_and_prompt():
    from scripts.prompts import load_prompts
    from scripts.arms import run_arms
    passages = run_arms(load_prompts()[:1], generate_v1=_stub("v1"), generate_v2=_stub("v2"))
    assert len(passages) == 2
    assert passages[0]["text"].startswith("[v1]")
    assert passages[1]["text"].startswith("[v2]")
