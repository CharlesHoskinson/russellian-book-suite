"""Load a mode-keyed system prompt from assets/system-prompts/<mode>.md."""
from __future__ import annotations

from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "system-prompts"

VALID_MODES = {"technical-exposition", "pedagogical-walkthrough", "popular-science"}
DEFAULT_MODE = "technical-exposition"


def available_modes() -> list[str]:
    return sorted(VALID_MODES)


def load_system_prompt(mode: str = DEFAULT_MODE) -> str:
    if mode not in VALID_MODES:
        raise ValueError(
            f"unknown prose mode: {mode!r}; valid modes: {sorted(VALID_MODES)}"
        )
    path = PROMPTS_DIR / f"{mode}.md"
    if not path.is_file():
        raise FileNotFoundError(f"system prompt not found: {path}")
    return path.read_text(encoding="utf-8")
