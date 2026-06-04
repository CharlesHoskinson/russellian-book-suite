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


def _best_single(bbag: set[str], after_bags: list[set[str]]) -> tuple[int, float]:
    """Best overlap against any one after-sentence; used for claim ordering."""
    best_i, best = -1, 0.0
    for ai, abag in enumerate(after_bags):
        if not abag:
            continue
        overlap = len(bbag & abag) / len(bbag)
        if overlap > best:
            best_i, best = ai, overlap
    return best_i, best


def _best_window(bbag: set[str], after_bags: list[set[str]], k: int = 3) -> float:
    """Best overlap against a window of up to k consecutive after-sentences.

    A Feynman pass may split one Russell sentence into several, so a claim's
    content words spread across consecutive after-sentences. Matching against the
    union of a short window recovers those split claims without weakening the
    drop test, since unrelated neighbours share few content words.
    """
    best = 0.0
    n = len(after_bags)
    for i in range(n):
        union: set[str] = set()
        for j in range(i, min(i + k, n)):
            union |= after_bags[j]
            overlap = len(bbag & union) / len(bbag)
            if overlap > best:
                best = overlap
    return best


def _longest_nondecreasing(seq: list[int]) -> int:
    import bisect
    tails: list[int] = []
    for x in seq:
        i = bisect.bisect_right(tails, x)
        if i == len(tails):
            tails.append(x)
        else:
            tails[i] = x
    return len(tails)


def preserve_argument(before: str, after: str, min_overlap: float = 0.30) -> PreservationReport:
    violations: list[dict] = []
    before_sents = _sentences(before)
    after_sents = _sentences(after)
    after_bags = [_content_words(s) for s in after_sents]

    matched_after_idx: list[int] = []
    for bi, bs in enumerate(before_sents):
        bbag = _content_words(bs)
        if not bbag:
            continue
        # Drop test uses a window union (tolerates sentence-splitting and synonym
        # swaps); ordering uses the single best sentence (so a real swap is caught).
        window_score = _best_window(bbag, after_bags)
        if window_score < min_overlap:
            violations.append({"kind": "dropped-claim", "claim": bs[:120], "score": round(window_score, 2)})
        else:
            best_i, _ = _best_single(bbag, after_bags)
            matched_after_idx.append(best_i)

    # Flag reordering only when claim order is substantially scrambled, not on a
    # single local move that a Feynman pass makes for flow. A near-fully-reversed
    # sequence (longest non-decreasing run below ~60% of claims) is a real reorder.
    if len(matched_after_idx) >= 2:
        keep = _longest_nondecreasing(matched_after_idx)
        if keep < max(2, (len(matched_after_idx) * 3 + 4) // 5):
            violations.append({"kind": "reordered-claim", "detail": "claim order not preserved"})

    before_nums = set(_NUM.findall(before))
    for n in _NUM.findall(after):
        if n not in before_nums:
            violations.append({"kind": "introduced-fact", "fact": n})
    before_proper = set(_PROPER.findall(before))
    for p in _PROPER.findall(after):
        if p not in before_proper:
            violations.append({"kind": "introduced-fact", "fact": p})

    return PreservationReport(ok=not violations, violations=violations)
