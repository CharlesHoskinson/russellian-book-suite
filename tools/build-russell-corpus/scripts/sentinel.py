"""Sentinel — six deterministic checks against a candidate corpus entry.

Returns a SentinelOutcome with status in {"pass", "reject", "defer"} and an optional reason
code. The orchestrator routes outcomes to passed-sentinel.jsonl / rejected.jsonl /
pending-tag.jsonl.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from scripts.corpus_io import (
    content_locator,
    paragraph_in_source,
    find_paragraph_line,
    read_index,
)


@dataclass
class SentinelOutcome:
    status: str  # "pass" | "reject" | "defer"
    reason: str | None
    evidence: dict[str, Any] | None
    corrected_line_hint: int | None = None


def _load_allow_list(path: Path) -> dict[str, dict[str, str]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {entry["source_id"]: entry for entry in data["allowed"]}


def _load_vocabulary(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {t["slug"] for t in data["tags"]}


def _load_generic_phrases(path: Path) -> list[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return list(data.get("phrases") or [])


def run_sentinel(
    *,
    candidate: dict[str, Any],
    source_path: Path,
    allow_list_path: Path,
    vocabulary_path: Path,
    generic_phrases_path: Path,
    existing_index_path: Path,
    batch_seen_locators: set[str],
) -> SentinelOutcome:
    """Run all six deterministic checks against a single candidate."""
    # Check 1: PD allow-list
    allow_list = _load_allow_list(allow_list_path)
    if candidate["source_id"] not in allow_list:
        return SentinelOutcome("reject", "not-pd-allowed", {"source_id": candidate["source_id"]})

    # Check 2: paragraph verbatim in source
    if not paragraph_in_source(candidate["paragraph_text"], source_path):
        return SentinelOutcome("reject", "source-mismatch", {"locator": content_locator(candidate["paragraph_text"])})

    # Check 3: locator alignment (line_hint correction)
    found_line = find_paragraph_line(content_locator(candidate["paragraph_text"]), source_path)
    if found_line is None:
        return SentinelOutcome("reject", "locator-not-found", {"locator": content_locator(candidate["paragraph_text"])})
    corrected = found_line if abs(found_line - candidate["line_hint"]) > 50 else None

    # Check 4: dedup against existing index and batch
    idx = read_index(existing_index_path)
    existing_locators = {
        content_locator(e.get("content_locator") or e.get("rhetorical_move", "")) for e in idx["paragraphs"]
    }
    cand_locator = content_locator(candidate["paragraph_text"])
    if cand_locator in existing_locators or cand_locator in batch_seen_locators:
        return SentinelOutcome("reject", "duplicate", {"locator": cand_locator})

    # Check 5: rhetorical_move_tag in controlled vocabulary
    vocabulary = _load_vocabulary(vocabulary_path)
    if candidate["rhetorical_move_tag"] not in vocabulary:
        return SentinelOutcome("defer", "novel-tag", {"proposed_tag": candidate["rhetorical_move_tag"]})

    # Check 6: generic-lesson surface filter
    generics = _load_generic_phrases(generic_phrases_path)
    lesson_lower = candidate["calibration_lesson"].lower()
    for phrase in generics:
        if phrase.lower() in lesson_lower:
            return SentinelOutcome("reject", "generic-lesson-filter", {"matched_phrase": phrase})

    return SentinelOutcome("pass", None, None, corrected_line_hint=corrected)
