"""Deterministic keyword router: topic -> register."""
from __future__ import annotations
import re

REGISTERS = ("technical-exposition", "narrative-editorial", "polemic")

_TECHNICAL = re.compile(
    r"\b(how does|how do|mechanic|construct|algorithm|protocol|implement|"
    r"formal|proof|prove|define|definition|architecture|circuit|equation|complexity)\b")
_POLEMIC = re.compile(
    r"\b(myth|wrong|everyone|everybody|stop saying|the truth about|overrated|"
    r"is a lie|debate|versus|vs\.?|critique|hype|should stop|nonsense)\b")


def route(topic: str) -> str:
    low = topic.lower()
    if _POLEMIC.search(low):
        return "polemic"
    if _TECHNICAL.search(low):
        return "technical-exposition"
    return "narrative-editorial"
