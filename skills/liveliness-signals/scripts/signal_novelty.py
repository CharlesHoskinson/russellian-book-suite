"""Advisory novelty-continuity scorer: adjacent-sentence content overlap corridor."""
from __future__ import annotations

_LOW = 0.05    # below -> jump cut
_HIGH = 0.6    # above -> restatement


def _jaccard(a: frozenset, b: frozenset) -> float:
    u = a | b
    return len(a & b) / len(u) if u else 0.0


def score(sentences, register, profile) -> dict:
    findings: list[dict] = []
    if len(sentences) < 2:
        return {"signal": "novelty_continuity", "score": 0.0, "findings": findings}
    in_band = 0
    pairs = 0
    for idx, (a, b) in enumerate(zip(sentences, sentences[1:])):
        pairs += 1
        j = _jaccard(a.content, b.content)
        if j <= _LOW:
            findings.append({"flag": "jump_cut", "pair_start": idx, "jaccard": round(j, 3)})
        elif j >= _HIGH:
            findings.append({"flag": "restatement", "pair_start": idx, "jaccard": round(j, 3)})
        else:
            in_band += 1
    return {"signal": "novelty_continuity", "score": round(in_band / pairs, 4) if pairs else 0.0,
            "findings": findings}
