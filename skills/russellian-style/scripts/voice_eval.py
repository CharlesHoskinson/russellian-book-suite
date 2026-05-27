"""Generate Russell-voice paragraphs and compare them to original Russell.

Advisory eval stage. Generation uses an injected LLM callable (no live calls).
Comparison uses the Russell-Delta scorer and the russellian-style linter battery.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional

from scripts.system_prompt_loader import load as load_prompt, VALID_MODES

DEFAULT_N = 30
DEFAULT_MODE = "technical-exposition"


def build_generation_prompt(topic: str, mode: str, n: int) -> str:
    contract = load_prompt(mode)
    return (
        f"{contract}\n\n"
        f"# Task\n"
        f"Write {n} paragraphs on the following topic, observing the contract above. "
        f"Topic: {topic}\n"
        f"Output only the prose: no headings, no preamble, no numbering."
    )


def generate_paragraphs(topic: str, mode: str = DEFAULT_MODE, n: int = DEFAULT_N,
                        *, llm_call: Callable[[str], str]) -> str:
    if mode not in VALID_MODES:
        raise ValueError(f"unknown mode: {mode!r}; valid: {sorted(VALID_MODES)}")
    return llm_call(build_generation_prompt(topic, mode, n))
