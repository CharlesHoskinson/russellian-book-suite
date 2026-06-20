# skills/voice-eval/scripts/signal_deltas.py
"""Per-signal mean deltas between the v2 and v1 arms (REQ-VEVAL-011).

The scorer is injected; ``default_scorer`` wires liveliness-signals.score_passage.
A delta is computed per prompt (v2 − v1) per signal, then averaged overall and within
each register.
"""
from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Callable

Scorer = Callable[[str, str, str, str], dict]   # (text, register, prompt_id, arm) -> {signal: {"score": float}}


def _index(passages: list[dict], scorer: Scorer, signals) -> dict:
    scores: dict = {}
    for p in passages:
        s = scorer(p["text"], p["register"], p["prompt_id"], p["arm"])
        scores[(p["prompt_id"], p["arm"])] = {sig: float(s[sig].get("score") or 0.0) for sig in signals}
    return scores


def compute_deltas(passages: list[dict], *, scorer: Scorer, signals) -> dict:
    scores = _index(passages, scorer, signals)
    registers = {p["prompt_id"]: p["register"] for p in passages}
    prompt_ids = sorted({p["prompt_id"] for p in passages})

    per_prompt = {}
    for pid in prompt_ids:
        if (pid, "v1") in scores and (pid, "v2") in scores:
            per_prompt[pid] = {sig: scores[(pid, "v2")][sig] - scores[(pid, "v1")][sig] for sig in signals}

    overall = {sig: mean(per_prompt[pid][sig] for pid in per_prompt) for sig in signals}

    by_reg = defaultdict(list)
    for pid, deltas in per_prompt.items():
        by_reg[registers[pid]].append(deltas)
    per_register = {
        reg: {sig: mean(d[sig] for d in rows) for sig in signals}
        for reg, rows in by_reg.items()
    }
    return {"overall": overall, "per_register": per_register, "per_prompt": per_prompt}


def default_scorer(text: str, register: str, prompt_id: str, arm: str) -> dict:
    """Adapt liveliness-signals.score_passage (which nests signals under "signals")
    to the {signal: {"score": float}} contract compute_deltas expects."""
    from scripts.sibling_skills import call
    result = call("liveliness-signals", "scripts.score", "score_passage", text, register)
    return result["signals"]
