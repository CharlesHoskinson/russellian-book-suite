"""Enumerate channel uploads via an injected fetch callable (scrapling-fetch boundary)."""

from __future__ import annotations

import json
from typing import Any, Callable


def extract_initial_data(html: str) -> dict[str, Any]:
    """Pull the ytInitialData JSON object out of channel page HTML.

    Uses brace matching (string- and escape-aware) rather than a regex, so a `};`
    or `};</script>` appearing inside a JSON string value (e.g. a video title) does
    not truncate the blob.
    """
    marker = html.find("ytInitialData")
    if marker == -1:
        raise ValueError("ytInitialData not found in page")
    start = html.find("{", marker)
    if start == -1:
        raise ValueError("ytInitialData object start not found")
    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(html)):
        ch = html[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(html[start : i + 1])
    raise ValueError("unbalanced braces in ytInitialData blob")


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


def discover_channel(channel_videos_url: str, *, fetch: Callable[[str], str]) -> list[dict[str, Any]]:
    """Fetch the channel /videos page and parse video rows.

    `fetch(url) -> html` is the injected scrapling-fetch boundary. v1 fetches the first
    page only; pagination via continuation tokens is a future extension.
    """
    html = fetch(channel_videos_url)
    data = extract_initial_data(html)
    return parse_video_entries(data)
