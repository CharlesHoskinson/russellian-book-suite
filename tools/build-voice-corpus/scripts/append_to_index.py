"""Assemble tagged passages into hoskinson-corpus/index.json entries."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.corpus_io import append_index_entries, read_index


def _next_indices(index_path: Path) -> dict[str, int]:
    """Seed the per-video passage counter from any existing index entries (4.3).

    Entry ids have the form ``hoskinson-<video_id>-<NNN>``; the next index for a
    video is one past the highest already present, so re-indexing a video does not
    collide with (or overwrite) entries from a prior run.
    """
    per_video: dict[str, int] = {}
    if not index_path.exists():
        return per_video
    for e in read_index(index_path).get("paragraphs", []):
        vid = e.get("video_id")
        if vid is None:
            continue
        try:
            n = int(str(e["id"]).rsplit("-", 1)[1])
        except (KeyError, ValueError, IndexError):
            continue
        per_video[vid] = max(per_video.get(vid, 0), n + 1)
    return per_video


def build_entry(*, video_id: str, index: int, t_start: str, text: str,
                rhetorical_move: str, tags: list[str]) -> dict[str, Any]:
    return {
        "id": f"hoskinson-{video_id}-{index:03d}",
        "video_id": video_id,
        "t_start": t_start,
        "text": text,
        "rhetorical_move": rhetorical_move,
        "tags": tags,
    }


def append_passages(index_path: Path, passages: list[dict[str, Any]]) -> None:
    """Each passage carries video_id, t_start, text, rhetorical_move, tags."""
    entries: list[dict[str, Any]] = []
    per_video: dict[str, int] = _next_indices(index_path)
    for p in passages:
        vid = p["video_id"]
        i = per_video.get(vid, 0)
        per_video[vid] = i + 1
        entries.append(build_entry(
            video_id=vid, index=i, t_start=p["t_start"], text=p["text"],
            rhetorical_move=p["rhetorical_move"], tags=p["tags"],
        ))
    append_index_entries(index_path, entries)
