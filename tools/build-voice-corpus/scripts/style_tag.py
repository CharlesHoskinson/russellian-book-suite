"""Tag a cleaned passage with a rhetorical move and manner tags via an injected LLM."""

from __future__ import annotations

import json
import re
from typing import Any, Callable

LlmCall = Callable[[str], str]
_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def build_prompt(passage: str, template: str) -> str:
    return template.replace("{passage}", passage)


_SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")


def parse_tag_response(raw: str) -> dict[str, Any]:
    text = raw.strip()
    m = _FENCE.search(text)
    if m:
        text = m.group(1)
    obj = json.loads(text)
    if "rhetorical_move" not in obj or "tags" not in obj:
        raise ValueError("response missing required keys")
    move = str(obj["rhetorical_move"]).strip()
    if not move:
        raise ValueError("rhetorical_move is empty")
    tags = obj["tags"]
    if not isinstance(tags, list):
        raise ValueError("tags must be a list")
    if not 1 <= len(tags) <= 4:
        raise ValueError("tags must contain 1 to 4 items")
    norm_tags = []
    for t in tags:
        t = str(t)
        if not _SNAKE.match(t):
            raise ValueError(f"tag {t!r} is not lowercase snake_case")
        norm_tags.append(t)
    return {"rhetorical_move": move, "tags": norm_tags}


def tag_passage(passage: str, *, llm_call: LlmCall, template: str) -> dict[str, Any]:
    return parse_tag_response(llm_call(build_prompt(passage, template)))
