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
    append_jsonl,
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

    # Check 4: dedup against existing index and batch.
    # Both sides key on the canonical locator = content_locator(paragraph_text). Index
    # entries persist that exact key under "content_locator" (see append_to_index), so we
    # compare against it directly with NO re-derivation and NO fallback to rhetorical_move
    # (a lesson string is not a paragraph prefix and would never match — it only produced
    # phantom keys that defeated cross-index dedup). Seed entries that predate the locator
    # field simply carry no key here and are not dedup-protected until backfilled.
    idx = read_index(existing_index_path)
    existing_locators = {
        e["content_locator"] for e in idx["paragraphs"] if e.get("content_locator")
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


def run_sentinel_batch(
    *,
    candidates_path: Path,
    source_cache_dir: Path,
    allow_list_path: Path,
    vocabulary_path: Path,
    generic_phrases_path: Path,
    existing_index_path: Path,
    run_dir: Path,
) -> None:
    """Iterate candidates.jsonl, route each outcome to the matching ledger."""
    run_dir.mkdir(parents=True, exist_ok=True)
    passed = run_dir / "passed-sentinel.jsonl"
    rejected = run_dir / "rejected.jsonl"
    pending = run_dir / "pending-tag.jsonl"
    proposed_tags = run_dir / "proposed-tags.jsonl"

    batch_locators: set[str] = set()
    proposed_seen: set[str] = set()
    allow_list = _load_allow_list(allow_list_path)

    with candidates_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            cand = json.loads(line)
            src_id = cand["source_id"]
            if src_id not in allow_list:
                append_jsonl(rejected, {"candidate_id": cand["candidate_id"], "reason": "not-pd-allowed", "evidence": {"source_id": src_id}})
                continue
            # Resolve the cached source file for this source_id. Convention: <cache>/<source_id>_subset.html for tests;
            # in production the cache layout matches scrapling-fetch's directory shape.
            source_path = source_cache_dir / f"{src_id}_subset.html"
            outcome = run_sentinel(
                candidate=cand,
                source_path=source_path,
                allow_list_path=allow_list_path,
                vocabulary_path=vocabulary_path,
                generic_phrases_path=generic_phrases_path,
                existing_index_path=existing_index_path,
                batch_seen_locators=batch_locators,
            )
            if outcome.status == "pass":
                if outcome.corrected_line_hint is not None:
                    cand["line_hint"] = outcome.corrected_line_hint
                append_jsonl(passed, cand)
                batch_locators.add(content_locator(cand["paragraph_text"]))
            elif outcome.status == "defer":
                append_jsonl(pending, cand)
                tag = cand["rhetorical_move_tag"]
                if tag not in proposed_seen:
                    append_jsonl(proposed_tags, {"tag": tag, "first_candidate_id": cand["candidate_id"]})
                    proposed_seen.add(tag)
            else:
                append_jsonl(rejected, {
                    "candidate_id": cand["candidate_id"],
                    "reason": outcome.reason,
                    "evidence": outcome.evidence,
                })
