"""Two-stage address check: verbatim fast path then cached LLM verifier."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable


def _cache_key(chapter: str, rival_text: str) -> str:
    h = hashlib.sha256()
    h.update(chapter.encode("utf-8"))
    h.update(b"||")
    h.update(rival_text.encode("utf-8"))
    return h.hexdigest()


def check_address(chapter_text: str, rival: dict,
                  verifier: Callable[[str, str], dict],
                  cache_dir: Path) -> dict:
    """Returns {addressed, mechanism, supporting_paragraph}.

    mechanism is one of: "verbatim" | "llm" | "none".
    """
    rival_text = rival["text"]
    if rival_text.strip() in chapter_text:
        return {"addressed": True, "mechanism": "verbatim",
                "supporting_paragraph": rival_text.strip()}
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _cache_key(chapter_text, rival_text)
    cache_file = cache_dir / f"{key}.json"
    if cache_file.exists():
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        return {"addressed": bool(cached["addressed"]),
                "mechanism": "llm",
                "supporting_paragraph": cached.get("supporting_paragraph")}
    verdict = verifier(chapter_text, rival_text)
    cache_file.write_text(json.dumps(verdict), encoding="utf-8")
    return {"addressed": bool(verdict["addressed"]),
            "mechanism": "llm",
            "supporting_paragraph": verdict.get("supporting_paragraph")}
