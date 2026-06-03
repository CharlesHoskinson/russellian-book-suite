"""Chapter-id parsing shared across halmos scripts."""
from __future__ import annotations
import re

_CH = re.compile(r"ch-?(\d+)")


def chapter_n(cid: str) -> int:
    """Chapter number from a 'ch-NN[-suffix]' id. Raises ValueError on a non-conforming id."""
    m = _CH.match(cid)
    if not m:
        raise ValueError(f"unrecognized chapter id: {cid!r}")
    return int(m.group(1))
