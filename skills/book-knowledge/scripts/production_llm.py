"""Production LLM callable for book-knowledge.

Tests use llm_call=fake_llm; production CLI uses default_llm_call().
"""

from __future__ import annotations

from typing import Callable

from llm_infra import make_ollama_call

DEFAULT_MODEL = "gemma4:31b"


def default_llm_call(model: str = DEFAULT_MODEL) -> Callable[[str], str]:
    """Build the production llm_call for book-knowledge."""
    return make_ollama_call(model=model)
