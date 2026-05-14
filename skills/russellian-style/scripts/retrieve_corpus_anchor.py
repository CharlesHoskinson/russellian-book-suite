"""Retrieve one Russell paragraph reference from the corpus index.

Returns a reference + lesson only. Per the russell-corpus-map.md
"do not paste full paragraphs into prompts by default" rule, the
full source text is never returned.

The corpus index has shape:
    {
        "version": "...",
        "sources": {<source_id>: {"title": ..., "url": ..., "mode": [...]}, ...},
        "paragraphs": [
            {"id": "...", "source": "<source_id>", "line_hint": int,
             "rhetorical_move": "...", "tags": [...]},
            ...
        ]
    }

retrieve_anchor accepts a `rhetorical_mode` argument that matches either:
- a `source` id directly (e.g. "problems"), or
- a value in any source's `mode` list (e.g. "popular_philosophy").
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


CORPUS_INDEX = (
    Path(__file__).resolve().parent.parent / "assets" / "russell-corpus" / "index.json"
)


@dataclass(frozen=True)
class ExemplarRef:
    corpus_id: str
    source_title: str
    source_url: str
    line_hint: int
    rhetorical_move: str
    calibration_lesson: str


def _load_index() -> dict:
    return json.loads(CORPUS_INDEX.read_text(encoding="utf-8"))


def _matches_mode(source_id: str, sources: dict, mode_filter: str) -> bool:
    if source_id == mode_filter:
        return True
    source_modes = sources.get(source_id, {}).get("mode", [])
    return mode_filter in source_modes


def retrieve_anchor(
    rhetorical_mode: str,
    rhetorical_move: Optional[str] = None,
    seed: int = 42,
) -> ExemplarRef:
    """Return one corpus entry matching the requested mode + (optional) move.

    Args:
        rhetorical_mode: source id (e.g. "problems") or mode tag (e.g.
            "popular_philosophy") from the sources block.
        rhetorical_move: optional substring filter against the
            rhetorical_move field or the tags list.
        seed: deterministic selection seed.

    Raises:
        ValueError: if no source matches the requested mode.
        LookupError: if a move filter is provided and matches nothing.
    """
    index = _load_index()
    sources = index["sources"]

    in_mode = [
        p for p in index["paragraphs"]
        if _matches_mode(p["source"], sources, rhetorical_mode)
    ]
    if not in_mode:
        raise ValueError(f"no corpus entries for mode: {rhetorical_mode!r}")

    if rhetorical_move:
        needle = rhetorical_move.lower()
        in_mode = [
            p for p in in_mode
            if needle in p.get("rhetorical_move", "").lower()
            or needle in " ".join(p.get("tags", [])).lower()
        ]
        if not in_mode:
            raise LookupError(
                f"no corpus entries for mode={rhetorical_mode!r} move~={rhetorical_move!r}"
            )

    rng = random.Random(seed)
    chosen = rng.choice(in_mode)
    source = sources.get(chosen["source"], {})
    return ExemplarRef(
        corpus_id=chosen["id"],
        source_title=source.get("title", ""),
        source_url=source.get("url", ""),
        line_hint=int(chosen.get("line_hint", 0)),
        rhetorical_move=chosen.get("rhetorical_move", ""),
        calibration_lesson=chosen.get("rhetorical_move", ""),
    )
