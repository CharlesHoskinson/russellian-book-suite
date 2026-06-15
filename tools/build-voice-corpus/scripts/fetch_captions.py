"""Fetch a video's captions via yt-dlp through an injected runner."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

Runner = Callable[[list[str]], Any]


def build_ytdlp_args(video_id: str, *, out_dir: Path, auto: bool, lang: str = "en") -> list[str]:
    """Build the yt-dlp argv for caption-only download (no media)."""
    sub_flag = "--write-auto-subs" if auto else "--write-subs"
    return [
        "yt-dlp",
        "--skip-download",
        sub_flag,
        "--sub-langs", lang,
        "--sub-format", "vtt",
        "--convert-subs", "vtt",
        "-o", str(out_dir / "%(id)s.%(ext)s"),
        f"https://www.youtube.com/watch?v={video_id}",
    ]


def _existing_vtt(video_id: str, out_dir: Path) -> Path | None:
    matches = sorted(out_dir.glob(f"{video_id}*.vtt"))
    return matches[0] if matches else None


def fetch_captions(video_id: str, *, out_dir: Path, runner: Runner, lang: str = "en") -> Path | None:
    """Try human subs, then auto subs. Return the VTT path, or None if neither exists."""
    out_dir.mkdir(parents=True, exist_ok=True)
    runner(build_ytdlp_args(video_id, out_dir=out_dir, auto=False, lang=lang))
    found = _existing_vtt(video_id, out_dir)
    if found:
        return found
    runner(build_ytdlp_args(video_id, out_dir=out_dir, auto=True, lang=lang))
    return _existing_vtt(video_id, out_dir)
