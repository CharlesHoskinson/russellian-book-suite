"""Network-free loader for the vendored Brysbaert concreteness lexicon."""
from __future__ import annotations
import csv
from functools import lru_cache
from pathlib import Path

_CSV = Path(__file__).resolve().parent.parent / "assets" / "concreteness-brysbaert.csv"


@lru_cache(maxsize=1)
def load_concreteness() -> dict:
    table: dict[str, float] = {}
    with open(_CSV, encoding="utf-8") as fh:
        reader = csv.reader(fh)
        next(reader, None)  # header
        for row in reader:
            if len(row) >= 2:
                try:
                    table[row[0]] = float(row[1])
                except ValueError:
                    continue
    return table


def conc(word: str, table: dict) -> float | None:
    w = word.lower()
    if w in table:
        return table[w]
    if w.endswith("s") and w[:-1] in table:
        return table[w[:-1]]
    return None
