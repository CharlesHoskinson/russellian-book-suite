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


def _dedup_lines(cues: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Rolling-window dedup across all cues.

    Returns a list of (t_start, line) pairs where t_start is the timestamp of
    the FIRST cue in which each distinct line appeared.  Lines that are
    identical to the immediately-preceding line (the hallmark of auto-sub
    repetition) are dropped.
    """
    result: list[tuple[str, str]] = []
    seen_last: str | None = None
    for t_start, body in cues:
        for line in body.splitlines():
            line = line.strip()
            if line and line != seen_last:
                result.append((t_start, line))
                seen_last = line
    return result


def dedupe_rolling(cues: list[tuple[str, str]]) -> str:
    """Collapse the rolling-window line repetition that auto-subs emit."""
    return " ".join(line for _, line in _dedup_lines(cues))


def strip_fragments(text: str, fragments: list[str]) -> str:
    for frag in fragments:
        text = text.replace(frag, "")
    return re.sub(r"\s+", " ", text).strip()


def segment_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def clean_vtt(
    text: str,
    *,
    stock_fragments: list[str],
    max_chars: int = 600,
) -> list[dict[str, str]]:
    """VTT text -> passages [{t_start, text}].

    1. Parses cues via parse_vtt.
    2. Applies rolling-window dedup across ALL cues via _dedup_lines.
    3. Strips stock fragments per line; drops lines that become empty.
    4. Groups consecutive surviving lines into passages up to max_chars chars.
       Each passage's t_start is the t_start of its first surviving line.
       Passage text is the space-joined lines, normalised via segment_sentences.
    """
    cues = parse_vtt(text)
    deduped = _dedup_lines(cues)

    # Strip stock fragments per line; track (t_start, cleaned_line) for survivors.
    survivors: list[tuple[str, str]] = []
    for t_start, line in deduped:
        cleaned = strip_fragments(line, stock_fragments)
        if cleaned:
            survivors.append((t_start, cleaned))

    # Group consecutive survivors into passages up to max_chars.
    out: list[dict[str, str]] = []
    passage_start: str | None = None
    passage_lines: list[str] = []
    current_len = 0

    def _flush() -> None:
        if not passage_lines:
            return
        raw = " ".join(passage_lines)
        # Use segment_sentences to normalise sentence spacing within the passage.
        normalised = " ".join(segment_sentences(raw)) if raw else raw
        if normalised and passage_start is not None:
            out.append({"t_start": passage_start, "text": normalised})

    for t_start, line in survivors:
        # +1 for the space separator when joining
        added = len(line) + (1 if passage_lines else 0)
        if passage_lines and current_len + added > max_chars:
            _flush()
            passage_lines = []
            passage_start = None
            current_len = 0

        if not passage_lines:
            passage_start = t_start
        passage_lines.append(line)
        current_len += added

    _flush()
    return out
