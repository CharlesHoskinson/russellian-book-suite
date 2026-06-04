# engine/report.py
"""Provenance-aware rendering.

The marked render is the default output so the user can see which words are
theirs (source), which are lightly edited (seam), and which are generated
(bridge). Both renders are produced from the same Segment list so marks cannot
drift from the text.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SegmentKind = Literal["source", "seam", "bridge"]

_MARK = {"source": "", "seam": "<!-- seam -->", "bridge": "<!-- bridge -->"}


@dataclass
class Segment:
    kind: SegmentKind
    text: str


def render_provenance(segments: list[Segment]) -> str:
    parts = []
    for s in segments:
        prefix = _MARK[s.kind]
        parts.append(f"{prefix}{s.text}" if prefix else s.text)
    return "\n\n".join(parts)


def render_clean(segments: list[Segment]) -> str:
    return "\n\n".join(s.text for s in segments)
