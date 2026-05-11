"""Deterministic AI-fingerprint detector for chapter drafts.

The actual humanizer rewrites happen via the `humanizer` Skill tool (invoked
by Claude during section drafting). This script measures residual fingerprints
so chapter_contract_check can gate on them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Patterns derived from the humanizer skill's documentation
_AI_VOCABULARY = [
    r"\bdelve\b", r"\bdelves into\b", r"\bnavigate\b", r"\bnavigates the\b",
    r"\btapestry\b", r"\bin the realm of\b", r"\bunderscore\b", r"\bunderscores\b",
    r"\bleverage\b", r"\bleverages\b", r"\bmeticulous\b", r"\bmeticulously\b",
    r"\bcomprehensive\b", r"\brobust\b", r"\bseamless\b", r"\bseamlessly\b",
    r"\bvibrant\b", r"\bbustling\b", r"\bever-evolving\b", r"\bever-changing\b",
    r"\bin today's\b", r"\bin the modern era\b", r"\bin recent years\b",
    r"\bit is important to note\b", r"\bit is worth noting\b",
    r"\bnot only .+? but also\b",
]
_FILLER = [
    r"\bin order to\b", r"\bdue to the fact that\b", r"\bat the end of the day\b",
    r"\bfor all intents and purposes\b", r"\bin the event that\b",
]
_INFLATED_SYMBOLISM = [
    r"\bthe heart of\b", r"\bat its core\b", r"\bthe essence of\b",
    r"\bthe spirit of\b", r"\bthe heartbeat of\b",
]


@dataclass(frozen=True)
class HumanizerResult:
    em_dash_count: int
    ai_vocab_count: int
    filler_count: int
    inflated_symbolism_count: int
    total_fingerprints: int
    matched_terms: list[str]


def assess_draft(draft_path: Path) -> HumanizerResult:
    text = Path(draft_path).read_text(encoding="utf-8")
    em_dashes = text.count("—")
    matched: list[str] = []
    ai_vocab = 0
    for pat in _AI_VOCABULARY:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            matched.append(m.group(0))
            ai_vocab += 1
    filler = 0
    for pat in _FILLER:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            matched.append(m.group(0))
            filler += 1
    inflated = 0
    for pat in _INFLATED_SYMBOLISM:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            matched.append(m.group(0))
            inflated += 1
    return HumanizerResult(
        em_dash_count=em_dashes,
        ai_vocab_count=ai_vocab,
        filler_count=filler,
        inflated_symbolism_count=inflated,
        total_fingerprints=ai_vocab + filler + inflated,
        matched_terms=matched,
    )


def main(argv: list[str]) -> int:
    import sys
    if len(argv) < 2:
        print("usage: humanizer_pass.py <draft.md>", file=sys.stderr)
        return 2
    r = assess_draft(Path(argv[1]))
    print(f"em_dashes: {r.em_dash_count}")
    print(f"ai_vocab: {r.ai_vocab_count}")
    print(f"filler: {r.filler_count}")
    print(f"inflated_symbolism: {r.inflated_symbolism_count}")
    print(f"total_fingerprints: {r.total_fingerprints}")
    if r.matched_terms:
        print("\nmatched terms:")
        for t in r.matched_terms[:20]:
            print(f"  - {t}")
    return 0 if r.total_fingerprints == 0 else 1


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv))
