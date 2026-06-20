# skills/voice-eval/scripts/floor_gate.py
"""Equal-grounding floor gate (REQ-VEVAL-010): every passage must clear the
russellian-style v1 floor. The battery is injected; ``default_battery`` wires the
real russellian-style 12-linter battery (v1 ruleset) via the sibling bridge.
"""
from __future__ import annotations

from typing import Callable

Battery = Callable[[str, str, str], int]   # (text, prompt_id, arm) -> violation count


def gate_passages(passages: list[dict], *, battery: Battery) -> dict:
    failures = []
    for p in passages:
        violations = battery(p["text"], p["prompt_id"], p["arm"])
        p["floor_violations"] = violations
        if violations > 0:
            failures.append({"prompt_id": p["prompt_id"], "arm": p["arm"], "violations": violations})
    return {"all_clean": not failures, "failures": failures, "n": len(passages)}


def default_battery(text: str, prompt_id: str, arm: str) -> int:
    """Real v1 floor battery via russellian-style.voice_eval.evaluate.

    evaluate() runs the 12 linters under the default (v1) ruleset and returns
    per-linter {count, per_1000}; the floor is clean iff every count is 0.
    """
    from scripts.sibling_skills import call
    report = call("russellian-style", "scripts.voice_eval", "evaluate", text)
    linters = report["generated"]["linters"]
    return sum(v["count"] for v in linters.values())
