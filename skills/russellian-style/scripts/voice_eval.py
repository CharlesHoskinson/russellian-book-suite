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


from scripts.score_russell_delta import score as _delta_score, load_profile, PROFILE_PATH
from scripts.lint_hedges import lint_hedges
from scripts.lint_passive_voice import lint_passive_voice
from scripts.lint_signal_density import lint_signal_density
from scripts.lint_parallel_structure import lint_parallel_structure
from scripts.lint_listicle_abstract import lint_listicle_abstract
from scripts.lint_sentence_rhythm import lint_sentence_rhythm
from scripts.lint_burstiness import lint_burstiness
from scripts.lint_ai_vocabulary import lint_ai_vocabulary
from scripts.lint_ai_staccato import lint_ai_staccato
from scripts.lint_concrete_instance_density import lint_concrete_instance_density
from scripts.lint_epistemic_precision import lint_epistemic_precision
from scripts.lint_paragraph_motion import lint_paragraph_motion

LINTERS = {
    "hedges": lint_hedges,
    "passive_voice": lint_passive_voice,
    "signal_density": lint_signal_density,
    "parallel_structure": lint_parallel_structure,
    "listicle_abstract": lint_listicle_abstract,
    "sentence_rhythm": lint_sentence_rhythm,
    "burstiness": lint_burstiness,
    "ai_vocabulary": lint_ai_vocabulary,
    "ai_staccato": lint_ai_staccato,
    "concrete_instance_density": lint_concrete_instance_density,
    "epistemic_precision": lint_epistemic_precision,
    "paragraph_motion": lint_paragraph_motion,
}


def _signals(text: str, profile: dict) -> dict:
    delta = _delta_score(text, profile)
    n_words = delta["n_words"]
    fd, name = tempfile.mkstemp(suffix=".md")
    os.close(fd)
    path = Path(name)
    try:
        path.write_text(text, encoding="utf-8")
        linters = {}
        for lname, fn in LINTERS.items():
            count = len(fn(path))
            per_1000 = round(count / n_words * 1000, 3) if n_words else 0.0
            linters[lname] = {"count": count, "per_1000": per_1000}
    finally:
        path.unlink(missing_ok=True)
    return {"russell_delta": delta, "n_words": n_words, "linters": linters}


def evaluate(generated_text: str, russell_baseline_text: Optional[str] = None,
             profile_path: Path = PROFILE_PATH) -> dict:
    profile = load_profile(profile_path)
    report = {"generated": _signals(generated_text, profile), "baseline": None}
    if russell_baseline_text is not None:
        report["baseline"] = _signals(russell_baseline_text, profile)
    return report
