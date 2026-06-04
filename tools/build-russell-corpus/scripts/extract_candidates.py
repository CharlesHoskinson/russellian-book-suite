"""LLM extractor: reads one PD Russell source, proposes N candidate corpus entries.

The LLM is parameterised via `llm_call: Callable[[str], str]` so tests pass stubs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from scripts.corpus_io import append_jsonl


def extract_candidates(
    *,
    source_path: Path,
    source_id: str,
    source_url: str,
    vocabulary_path: Path,
    prompt_path: Path,
    out_path: Path,
    n: int,
    llm_call: Callable[[str], str],
) -> None:
    """Read source, build the extractor prompt, call the LLM, write candidates.jsonl."""
    source_text = source_path.read_text(encoding="utf-8")
    vocabulary = vocabulary_path.read_text(encoding="utf-8")
    prompt_template = prompt_path.read_text(encoding="utf-8")
    prompt = (
        prompt_template
        .replace("{{SOURCE_TEXT}}", source_text)
        .replace("{{VOCABULARY}}", vocabulary)
        .replace("{{N}}", str(n))
        .replace("{{SOURCE_ID}}", source_id)
        .replace("{{SOURCE_URL}}", source_url)
    )
    raw = llm_call(prompt)
    candidates = _parse_candidates(raw)
    # Genuinely empty output (model found nothing) is fine. But non-empty output that
    # parses to zero candidates is a contract violation we must surface here rather than
    # writing an empty file and deferring to a confusing zero-candidate sentinel run.
    if not candidates:
        if raw.strip():
            raise ValueError(
                "extract_candidates: LLM returned non-empty output but parsed 0 candidates "
                "(expected JSONL — one JSON object per line — or a top-level JSON array). "
                f"First 200 chars of output: {raw.strip()[:200]!r}"
            )
        return
    for obj in candidates:
        append_jsonl(out_path, obj)


def _parse_candidates(raw: str) -> list[dict]:
    """Parse candidate objects from an LLM response.

    Accepts both the JSONL contract (one JSON object per line) and a top-level JSON
    array (a common LLM deviation, including pretty-printed multi-line output). Returns
    the list of parsed dict candidates; malformed individual lines are skipped.
    """
    stripped = raw.strip()
    if not stripped:
        return []
    # First, try the whole response as a single JSON value (handles a pretty-printed
    # top-level array or a single multi-line object that JSONL-line parsing would miss).
    try:
        whole = json.loads(stripped)
    except json.JSONDecodeError:
        whole = None
    if isinstance(whole, list):
        return [obj for obj in whole if isinstance(obj, dict)]
    if isinstance(whole, dict):
        return [whole]
    # Fall back to line-by-line JSONL parsing; skip malformed lines.
    candidates: list[dict] = []
    for line in stripped.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            candidates.append(obj)
    return candidates
