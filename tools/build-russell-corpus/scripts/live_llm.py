"""Anthropic-SDK wrapper exposing extract_llm, cross_check_llm, and generate.

Production code uses these; tests pass stubs to the stage callables instead.
The module deliberately raises a clear RuntimeError when ANTHROPIC_API_KEY is
unset rather than letting the SDK fail mid-network-call.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


_CONFIG_PATH = Path(__file__).parent.parent / "assets" / "llm-config.yaml"


def _load_config() -> dict[str, Any]:
    return yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8"))


def _client():
    """Construct an Anthropic client. Raises RuntimeError if the API key is missing."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set in environment; cannot call Anthropic API."
        )
    from anthropic import Anthropic  # lazy import so the module loads without the SDK installed
    return Anthropic()


def _call(prompt: str, *, model: str, max_tokens: int, temperature: float) -> str:
    client = _client()
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(getattr(block, "text", "") for block in msg.content)


def extract_llm(prompt: str) -> str:
    """Run the corpus extractor model on a prompt and return the text."""
    cfg = _load_config()["extract"]
    return _call(prompt, model=cfg["model_id"], max_tokens=cfg["max_tokens"],
                 temperature=cfg["temperature"])


def cross_check_llm(prompt: str) -> str:
    """Run the cross-check verifier model on a prompt and return the text."""
    cfg = _load_config()["cross_check"]
    return _call(prompt, model=cfg["model_id"], max_tokens=cfg["max_tokens"],
                 temperature=cfg["temperature"])


def generate(prompt: str, *, model: str = "claude-opus-4-7",
             max_tokens: int = 8192, temperature: float = 0.7) -> str:
    """General-purpose generation. Used by the audit's sample-text stage."""
    return _call(prompt, model=model, max_tokens=max_tokens, temperature=temperature)
