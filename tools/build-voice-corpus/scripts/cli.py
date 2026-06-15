"""Orchestrate discover -> sample -> fetch -> clean -> tag over a resumable manifest."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import yaml

from scripts import manifest
from scripts.append_to_index import append_passages
from scripts.clean import clean_vtt
from scripts.corpus_io import init_index
from scripts.discover import discover_channel
from scripts.fetch_captions import fetch_captions
from scripts.sample import sample
from scripts.style_tag import tag_passage

_ASSETS = Path(__file__).parents[1] / "assets"


def _load_stock_fragments() -> list[str]:
    return yaml.safe_load((_ASSETS / "stock-fragments.yaml").read_text(encoding="utf-8"))["fragments"]


def _load_template() -> str:
    return (_ASSETS / "extractor-prompt.md").read_text(encoding="utf-8")


def run(*, channel_videos_url: str, workdir: Path, index_path: Path,
        fetch: Callable[[str], str], ytdlp_runner: Callable[[list[str]], Any],
        llm_call: Callable[[str], str], target: int, seed: int,
        max_passages_per_video: int = 20) -> dict[str, int]:
    """Run the full pipeline. Returns a stage summary. Resumable via manifest.jsonl."""
    workdir = Path(workdir)
    manifest_path = workdir / "manifest.jsonl"
    captions_dir = workdir / "captions"
    stock = _load_stock_fragments()
    template = _load_template()
    init_index(index_path, version="0.1.0",
               copyright_policy="Channel owner's own spoken content; transcripts stored inline.",
               sources={"channel": channel_videos_url})

    rows = discover_channel(channel_videos_url, fetch=fetch)
    state_now = manifest.latest_state(manifest_path)
    for r in rows:
        vid = r["video_id"]
        if vid not in state_now:
            manifest.record(manifest_path, vid, "discovered")

    chosen = sample(rows, target=target, seed=seed)
    by_id = {r["video_id"] for r in chosen}
    state_now = manifest.latest_state(manifest_path)
    for vid in by_id:
        row = state_now.get(vid)
        if row is None or row["stage"] == "discovered":
            manifest.record(manifest_path, vid, "sampled")

    todo = manifest.pending(manifest_path, sorted(by_id), target="tagged")
    summary = {"discovered": len(rows), "sampled": len(by_id), "tagged": 0, "skipped": 0}

    for vid in todo:
        vtt = fetch_captions(vid, out_dir=captions_dir, runner=ytdlp_runner)
        if vtt is None:
            manifest.record(manifest_path, vid, "skipped", reason="no_captions")
            summary["skipped"] += 1
            continue
        manifest.record(manifest_path, vid, "fetched")
        passages = clean_vtt(vtt.read_text(encoding="utf-8"), stock_fragments=stock)[:max_passages_per_video]
        manifest.record(manifest_path, vid, "cleaned")
        tagged: list[dict[str, Any]] = []
        for p in passages:
            tags = tag_passage(p["text"], llm_call=llm_call, template=template)
            tagged.append({"video_id": vid, "t_start": p["t_start"], "text": p["text"],
                           "rhetorical_move": tags["rhetorical_move"], "tags": tags["tags"]})
        if tagged:
            append_passages(index_path, tagged)
        manifest.record(manifest_path, vid, "tagged")
        summary["tagged"] += 1

    # Count already-tagged videos from prior runs so the summary reflects total state.
    state = manifest.latest_state(manifest_path)
    summary["tagged"] = sum(1 for v in state.values() if v["stage"] == "tagged")
    summary["skipped"] = sum(1 for v in state.values() if v["stage"] == "skipped")
    return summary
