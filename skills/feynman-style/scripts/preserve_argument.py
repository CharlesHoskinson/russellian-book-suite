"""preserve_argument: verify the Feynman pass did not change the argument.

Hard gate. Deterministic, model-free. Compares the Russell input (before) to
the Feynman output (after).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_STOP = {
    "the", "a", "an", "and", "or", "but", "if", "then", "so", "to", "of", "in",
    "on", "for", "is", "are", "was", "were", "be", "been", "it", "this", "that",
    "these", "those", "as", "at", "by", "with", "from", "into", "you", "your",
    "we", "our", "they", "their", "i", "he", "she", "his", "her", "its", "now",
    "here", "well", "just", "really", "out", "up", "off", "about", "what", "why",
    "how", "when", "where", "which", "who", "will", "would", "can", "could",
}
# Known v0.1 limitation: only digit-form numbers are detected. A spelled-out
# number in `before` ("three") vs a digit in `after` ("3") will false-positive
# as an introduced-fact; the reverse (digit before, word after) false-negatives.
_NUM = re.compile(r"\b\d+(?:[.,]\d+)?\b")
# Known v0.1 gate gap: only multi-word proper terms are detected. Single proper
# nouns (e.g. "Einstein", "Bitcoin") are NOT caught and can slip through.
_PROPER = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")


@dataclass
class PreservationReport:
    ok: bool
    violations: list[dict] = field(default_factory=list)


def _content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if w not in _STOP and len(w) > 2}


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def preserve_argument(before: str, after: str, min_overlap: float = 0.34) -> PreservationReport:
    violations: list[dict] = []
    before_sents = _sentences(before)
    after_sents = _sentences(after)
    after_bags = [_content_words(s) for s in after_sents]

    matched_after_idx: list[int] = []
    for bi, bs in enumerate(before_sents):
        bbag = _content_words(bs)
        if not bbag:
            continue
        best_i, best_score = -1, 0.0
        for ai, abag in enumerate(after_bags):
            if not abag:
                continue
            overlap = len(bbag & abag) / len(bbag)
            if overlap > best_score:
                best_i, best_score = ai, overlap
        if best_score < min_overlap:
            violations.append({"kind": "dropped-claim", "claim": bs[:120], "score": round(best_score, 2)})
        else:
            matched_after_idx.append(best_i)

    for a, b in zip(matched_after_idx, matched_after_idx[1:]):
        if b < a:
            violations.append({"kind": "reordered-claim", "detail": f"after-sentence {b} precedes {a}"})
            break

    before_nums = set(_NUM.findall(before))
    for n in _NUM.findall(after):
        if n not in before_nums:
            violations.append({"kind": "introduced-fact", "fact": n})
    before_proper = set(_PROPER.findall(before))
    for p in _PROPER.findall(after):
        if p not in before_proper:
            violations.append({"kind": "introduced-fact", "fact": p})

    return PreservationReport(ok=not violations, violations=violations)
