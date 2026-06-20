# skills/voice-eval/scripts/prompts.py
"""Load and validate the 20-prompt stratified set (REQ-VEVAL-009)."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

_ASSET = Path(__file__).resolve().parents[1] / "assets" / "prompts-20x20.json"

REGISTERS = ("technical-exposition", "narrative-editorial", "polemic")
EXPECTED_COUNTS = {"technical-exposition": 7, "narrative-editorial": 7, "polemic": 6}


class PromptSetError(ValueError):
    pass


def register_counts(prompts: list[dict]) -> dict:
    return dict(Counter(p["register"] for p in prompts))


def validate_prompts(prompts: list[dict]) -> list[dict]:
    if len(prompts) != 20:
        raise PromptSetError(f"expected 20 prompts, got {len(prompts)}")
    ids = [p["id"] for p in prompts]
    if len(set(ids)) != len(ids):
        raise PromptSetError("duplicate prompt ids")
    for p in prompts:
        if p.get("register") not in REGISTERS:
            raise PromptSetError(f"prompt {p.get('id')!r}: bad register {p.get('register')!r}")
        if not str(p.get("topic", "")).strip():
            raise PromptSetError(f"prompt {p.get('id')!r}: empty topic")
    if register_counts(prompts) != EXPECTED_COUNTS:
        raise PromptSetError(f"stratification must be {EXPECTED_COUNTS}, got {register_counts(prompts)}")
    return prompts


def load_prompts(path: Path = _ASSET) -> list[dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_prompts(payload["prompts"])
