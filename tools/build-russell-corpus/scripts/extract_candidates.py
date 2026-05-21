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
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            # malformed LLM output: skip line; sentinel will catch absence downstream
            continue
        append_jsonl(out_path, obj)
