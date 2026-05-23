"""Production LLM callable for syntopical-metabook.

The v0.3 acquire/synthesize/lens/gap sub-workflows (currently scaffolded but
inactive) will consume this. v0.2 governance positions does not consume LLM.
"""

from __future__ import annotations

from typing import Callable

from llm_infra import make_ollama_call

DEFAULT_MODEL = "gemma4:31b"


def default_llm_call(model: str = DEFAULT_MODEL) -> Callable[[str], str]:
    """Build the production llm_call for syntopical-metabook."""
    return make_ollama_call(model=model)
