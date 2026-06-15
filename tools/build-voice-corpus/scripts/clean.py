"""Clean WebVTT caption files into exemplar passages."""

from __future__ import annotations

import re

_TIMING = re.compile(r"^(\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2}\.\d{3})")
_TAG = re.compile(r"<[^>]+>")


def parse_vtt(text: str) -> list[tuple[str, str]]:
    """Return [(t_start, caption_text)] cues. Strips inline cue tags."""
    cues: list[tuple[str, str]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = _TIMING.match(lines[i].strip())
        if not m:
            i += 1
            continue
        t_start = m.group(1)
        i += 1
        body: list[str] = []
        while i < len(lines) and lines[i].strip() and not _TIMING.match(lines[i].strip()):
            body.append(_TAG.sub("", lines[i]).strip())
            i += 1
        cues.append((t_start, "\n".join(body).strip()))
    return cues


def dedupe_rolling(cues: list[tuple[str, str]]) -> str:
    """Collapse the rolling-window line repetition that auto-subs emit."""
    seen: list[str] = []
    for _, body in cues:
        for line in body.splitlines():
            line = line.strip()
            if line and (not seen or seen[-1] != line):
                seen.append(line)
    return " ".join(seen)


def strip_fragments(text: str, fragments: list[str]) -> str:
    for frag in fragments:
        text = text.replace(frag, "")
    return re.sub(r"\s+", " ", text).strip()


def segment_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def clean_vtt(text: str, *, stock_fragments: list[str]) -> list[dict[str, str]]:
    """VTT text -> passages [{t_start, text}]. One passage per non-empty cue, cleaned."""
    cues = parse_vtt(text)
    out: list[dict[str, str]] = []
    prev_line: str | None = None
    for t_start, body in cues:
        kept: list[str] = []
        for line in body.splitlines():
            line = line.strip()
            if line and line != prev_line:
                kept.append(line)
                prev_line = line
        merged = strip_fragments(" ".join(kept), stock_fragments)
        if merged:
            out.append({"t_start": t_start, "text": merged})
    return out
