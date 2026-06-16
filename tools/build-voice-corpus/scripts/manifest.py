"""Resumable per-video state, stored as an append-only JSONL ledger."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

STAGES = ["discovered", "sampled", "fetched", "cleaned", "tagged"]
SKIPPED = "skipped"


def record(path: Path, video_id: str, stage: str, **extra: Any) -> None:
    """Append one state row. `stage` is a STAGES value or 'skipped'."""
    if stage != SKIPPED and stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"video_id": video_id, "stage": stage, **extra}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def latest_state(path: Path) -> dict[str, dict[str, Any]]:
    """Return {video_id: latest_row}. Last write wins."""
    state: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return state
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            state[row["video_id"]] = row
    return state


def pending(path: Path, video_ids: list[str], *, target: str) -> list[str]:
    """Video ids not yet at `target` stage and not skipped, preserving input order."""
    state = latest_state(path)
    target_rank = STAGES.index(target)
    out: list[str] = []
    for vid in video_ids:
        row = state.get(vid)
        if row is None:
            out.append(vid)
            continue
        if row["stage"] == SKIPPED:
            continue
        if STAGES.index(row["stage"]) < target_rank:
            out.append(vid)
    return out
