"""Enumerate channel uploads via an injected fetch callable (scrapling-fetch boundary)."""

from __future__ import annotations

import json
import re
from typing import Any, Callable

_INITIAL = re.compile(r"ytInitialData\s*=\s*(\{.*?\})\s*;</script>", re.DOTALL)
_INITIAL_LOOSE = re.compile(r"ytInitialData\s*=\s*(\{.*?\});", re.DOTALL)


def extract_initial_data(html: str) -> dict[str, Any]:
    """Pull the ytInitialData JSON blob out of channel page HTML."""
    m = _INITIAL.search(html) or _INITIAL_LOOSE.search(html)
    if not m:
        raise ValueError("ytInitialData not found in page")
    return json.loads(m.group(1))


def hms_to_seconds(text: str) -> int:
    parts = [int(p) for p in text.split(":")]
    seconds = 0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds


def _walk_video_renderers(node: Any):
    """Yield every videoRenderer dict anywhere in the tree."""
    if isinstance(node, dict):
        if "videoRenderer" in node:
            yield node["videoRenderer"]
        for v in node.values():
            yield from _walk_video_renderers(v)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_video_renderers(item)


def parse_video_entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for vr in _walk_video_renderers(data):
        vid = vr.get("videoId")
        if not vid or vid in seen:
            continue
        seen.add(vid)
        title = "".join(r["text"] for r in vr.get("title", {}).get("runs", [])) or ""
        length_text = vr.get("lengthText", {}).get("simpleText", "0:00")
        published = vr.get("publishedTimeText", {}).get("simpleText", "")
        rows.append({
            "video_id": vid,
            "title": title,
            "published": published,
            "duration_seconds": hms_to_seconds(length_text),
        })
    return rows


def discover_channel(channel_videos_url: str, *, fetch: Callable[[str], str], max_pages: int = 20) -> list[dict[str, Any]]:
    """Fetch the channel /videos page(s) and parse video rows.

    `fetch(url) -> html` is the injected scrapling-fetch boundary. Pagination beyond
    the first page requires continuation handling; v1 fetches the first page and is
    capped by max_pages (continuation wiring is a documented later extension).
    """
    html = fetch(channel_videos_url)
    data = extract_initial_data(html)
    return parse_video_entries(data)
