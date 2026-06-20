"""Anti-copy alarm: flag verbatim n-gram overlap with the corpus + taboo phrases."""
from __future__ import annotations
import re

_WORD = re.compile(r"[a-z0-9']+")


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def word_ngrams(text: str, n: int = 4) -> set:
    toks = _tokens(text)
    return {tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def check(draft: str, corpus_texts: list[str], taboo: list[str] = ()) -> dict:
    draft_grams = word_ngrams(draft, 4)
    corpus_grams: set = set()
    for t in corpus_texts:
        corpus_grams |= word_ngrams(t, 4)
    shared = sorted(" ".join(g) for g in (draft_grams & corpus_grams))
    low = draft.lower()
    taboo_hits = [p for p in taboo if p.lower() in low]
    return {"shared_ngrams": shared, "taboo_hits": taboo_hits,
            "alarm": bool(shared or taboo_hits)}
