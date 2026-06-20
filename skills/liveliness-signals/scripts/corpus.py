"""Load the Hoskinson corpus and infer a register per paragraph.

Register is inferred deterministically by majority vote over a tag->register map,
defaulting to narrative-editorial on a tie or when no tag is recognized. The map is
a starting heuristic; an optional override file can be layered later.
"""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

REGISTERS = ("technical-exposition", "narrative-editorial", "polemic")
_DEFAULT_REGISTER = "narrative-editorial"

_TAG_REGISTER = {
    "systems_tradeoff": "technical-exposition",
    "problem_framing": "technical-exposition",
    "compression": "technical-exposition",
    "caution": "technical-exposition",
    "concrete_analogy": "narrative-editorial",
    "historical_analogy": "narrative-editorial",
    "scale_setting": "narrative-editorial",
    "signature_open": "narrative-editorial",
    "humane": "narrative-editorial",
    "incrementalism": "narrative-editorial",
    "conviction": "polemic",
    "momentum": "polemic",
    "candor": "polemic",
    "direct_address": "polemic",
    "maxim": "polemic",
    "deflation": "polemic",
    "forward_looking": "polemic",
    "inevitability": "polemic",
}


def register_for(tags: list[str], rhetorical_move: str) -> str:
    votes = Counter(_TAG_REGISTER[t] for t in (tags or []) if t in _TAG_REGISTER)
    if not votes:
        return _DEFAULT_REGISTER
    top = votes.most_common()
    if len(top) > 1 and top[0][1] == top[1][1]:
        return _DEFAULT_REGISTER
    return top[0][0]


def load_corpus(index_path: Path) -> list[dict]:
    data = json.loads(Path(index_path).read_text(encoding="utf-8"))
    rows = []
    for p in data.get("paragraphs", []):
        rows.append({
            "id": p["id"],
            "text": p.get("text", ""),
            "register": register_for(p.get("tags", []), p.get("rhetorical_move", "")),
        })
    return rows
