"""Tag a cleaned passage with a rhetorical move and manner tags via an injected LLM."""

from __future__ import annotations

import json
import re
from typing import Any, Callable

LlmCall = Callable[[str], str]
_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def build_prompt(passage: str, template: str) -> str:
    return template.replace("{passage}", passage)


def parse_tag_response(raw: str) -> dict[str, Any]:
    text = raw.strip()
    m = _FENCE.search(text)
    if m:
        text = m.group(1)
    obj = json.loads(text)
    if "rhetorical_move" not in obj or "tags" not in obj:
        raise ValueError("response missing required keys")
    if not isinstance(obj["tags"], list):
        raise ValueError("tags must be a list")
    return {"rhetorical_move": str(obj["rhetorical_move"]), "tags": [str(t) for t in obj["tags"]]}


def tag_passage(passage: str, *, llm_call: LlmCall, template: str) -> dict[str, Any]:
    return parse_tag_response(llm_call(build_prompt(passage, template)))
