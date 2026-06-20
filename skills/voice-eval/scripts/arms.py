# skills/voice-eval/scripts/arms.py
"""Run the two generation arms over the prompt set (REQ-VEVAL-009).

Generation is performed in-session by the running model; here it is an injected
``Callable[[dict], str]`` that receives a prompt dict and returns prose. Tests stub it.
"""
from __future__ import annotations

from typing import Callable

Passage = dict
Generator = Callable[[dict], str]


def run_arms(prompts: list[dict], *, generate_v1: Generator, generate_v2: Generator) -> list[Passage]:
    passages: list[Passage] = []
    for arm, gen in (("v1", generate_v1), ("v2", generate_v2)):
        for p in prompts:
            text = gen(p)
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"empty generation for {p['id']} ({arm})")
            passages.append({
                "prompt_id": p["id"],
                "register": p["register"],
                "arm": arm,
                "text": text,
            })
    return passages
