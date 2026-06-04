"""Generate three 15-paragraph sample texts via the three system prompts.

Each call uses claude-opus-4-7 at temperature 0.7 (higher than the corpus pipelines'
temperatures because we want creative prose). The output is the raw LLM response,
written verbatim to disk for linting by lint_samples.py.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_RUSSELLIAN_STYLE_ROOT = _REPO_ROOT / "skills" / "russellian-style"
_BUILD_TOOL = _REPO_ROOT / "tools" / "build-russell-corpus"


def _load_module_by_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Load russellian-style system_prompt_loader
_system_prompt_loader = _load_module_by_path(
    "russellian_style_system_prompt_loader",
    _RUSSELLIAN_STYLE_ROOT / "scripts" / "system_prompt_loader.py",
)
load_system_prompt = _system_prompt_loader.load

# Load live_llm — handle the same scripts.* collision pattern that expansion.py worked around.
# If expansion.py already pre-registered scripts.live_llm in sys.modules, this is a no-op.
if "scripts.live_llm" in sys.modules:
    _live_llm = sys.modules["scripts.live_llm"]
else:
    _live_llm = _load_module_by_path(
        "scripts.live_llm",
        _BUILD_TOOL / "scripts" / "live_llm.py",
    )
generate = _live_llm.generate


_TOPICS = {
    "technical-exposition": (
        "Why book-knowledge's claim ledger enforces a five-state machine "
        "(proposed -> verified -> disputed -> superseded -> refuted) instead of a "
        "free-form status field. What invariants the five states preserve, what they "
        "make impossible, and what they cost. Treat the reader as an attentive engineer "
        "who has not seen this codebase."
    ),
    "narrative-editorial": (
        "A chapter introduction for a book on the difference between what machines "
        "understand and what they recognize. The chapter is the first the reader meets; "
        "it has to set the question without answering it. Open with a concrete scene, "
        "name at least one specific person or institution, and end on a sentence that "
        "changes the question's pressure."
    ),
    "polemic": (
        "An op-ed against the listicle as a form of thought. Argue that ranked lists "
        "conceal the relations between their items and that the cost of that "
        "concealment is borne by the reader, not the writer. Personify at least one "
        "defender of the form. Close on a sentence that reverses the opener."
    ),
}


def generate_sample(mode: str, out_path: Path, *, generate_fn=None) -> dict:
    """Generate a 15-paragraph sample for the given mode. Write to out_path.

    Returns a dict with mode, char_count, and counted_paragraphs (by leading-number regex).
    """
    if mode not in _TOPICS:
        raise ValueError(f"unknown mode: {mode!r}")
    if generate_fn is None:
        generate_fn = generate
    system_prompt = load_system_prompt(mode)
    topic = _TOPICS[mode]
    full_prompt = (
        f"{system_prompt}\n\n"
        "# Writing task\n\n"
        "Write exactly 15 paragraphs on the following topic. Number each paragraph "
        "(1. through 15.). Each paragraph must perform one of the controlled Russell "
        "rhetorical moves; do not repeat the same move twice in a row.\n\n"
        f"## Topic\n\n{topic}\n"
    )
    text = generate_fn(full_prompt, model="claude-opus-4-7", max_tokens=8192, temperature=0.7)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    counted = len(re.findall(r"(?m)^\s*\d+\.\s", text))
    return {"mode": mode, "char_count": len(text), "counted_paragraphs": counted}


def generate_all_samples(out_dir: Path, *, generate_fn=None) -> list[dict]:
    """Generate samples for all three modes. Returns list of result dicts."""
    return [generate_sample(mode, out_dir / f"{mode}.md", generate_fn=generate_fn) for mode in _TOPICS]
