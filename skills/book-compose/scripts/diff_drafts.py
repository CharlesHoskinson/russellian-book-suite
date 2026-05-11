"""Compare two draft versions."""
from __future__ import annotations

import re
from pathlib import Path

_SECTION = re.compile(r"^(#{2,6})\s+(.+)$", re.MULTILINE)


def _sections(text: str) -> list[str]:
    return [m.group(0) for m in _SECTION.finditer(text)]


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text))


def diff_drafts(old: Path, new: Path) -> dict:
    a = Path(old).read_text(encoding="utf-8")
    b = Path(new).read_text(encoding="utf-8")
    a_secs = _sections(a)
    b_secs = _sections(b)
    return {
        "added_sections":   [s for s in b_secs if s not in a_secs],
        "removed_sections": [s for s in a_secs if s not in b_secs],
        "word_delta":       _word_count(b) - _word_count(a),
    }
