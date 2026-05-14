"""Epistemic precision linter.

Three categories replacing the binary hedge model:
1. banned_vague: vague hedges (perhaps, arguably, ...). Always flagged.
2. allowed_bounded: numeric/conditional constraints. Recognised, not flagged.
3. required_uncertainty: numeric specificity lacking a source attribution.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .lint_common import iter_sentences, load_markdown


_BANNED_VAGUE = [
    "perhaps", "arguably", "to some extent", "in some sense",
    "to a certain extent", "it could be argued", "many would say",
    "it might be suggested",
]

_ALLOWED_BOUNDED_PATTERNS = [
    re.compile(r"\bwithin\s+\d+\s*%", re.IGNORECASE),
    re.compile(r"\bunder\s+condition\b", re.IGNORECASE),
    re.compile(r"\bin\s+cases\s+where\b", re.IGNORECASE),
    re.compile(r"\bup\s+to\s+\d+\b", re.IGNORECASE),
    re.compile(r"\bat\s+least\s+\d+\b", re.IGNORECASE),
]

_NUMERIC_SPECIFICITY = re.compile(
    r"\b(\d{1,4}(?:\.\d+)?(?:%)?|\d{1,4}(?:st|nd|rd|th))\b"
)

_ATTRIBUTION_HINTS = re.compile(
    r"\b(source|cited|according to|reports?|per\s+\w+|\[clm-\d+-\d+\])\b",
    re.IGNORECASE,
)


def _banned_vague_pattern() -> re.Pattern:
    return re.compile(
        r"\b(" + "|".join(
            re.escape(p) for p in sorted(_BANNED_VAGUE, key=len, reverse=True)
        ) + r")\b",
        flags=re.IGNORECASE,
    )


def lint_epistemic_precision(path: Path) -> list[dict]:
    text = load_markdown(path)
    findings: list[dict] = []

    banned_re = _banned_vague_pattern()
    for sentence in iter_sentences(text):
        for m in banned_re.finditer(sentence.text):
            findings.append({
                "rule": "epistemic-precision",
                "category": "banned_vague",
                "phrase": m.group(1),
                "sentence": sentence.text,
                "line": getattr(sentence, "line", 0),
                "severity": "important",
            })

    sentences = list(iter_sentences(text))
    for i, sentence in enumerate(sentences):
        if not _NUMERIC_SPECIFICITY.search(sentence.text):
            continue
        if any(p.search(sentence.text) for p in _ALLOWED_BOUNDED_PATTERNS):
            continue
        if _ATTRIBUTION_HINTS.search(sentence.text):
            continue
        if i > 0 and _ATTRIBUTION_HINTS.search(sentences[i - 1].text):
            continue
        findings.append({
            "rule": "epistemic-precision",
            "category": "required_uncertainty",
            "sentence": sentence.text,
            "line": getattr(sentence, "line", 0),
            "severity": "advisory",
            "message": "Numeric specificity without source attribution in this sentence or the previous one.",
        })

    return findings


if __name__ == "__main__":
    import sys
    print(json.dumps(lint_epistemic_precision(Path(sys.argv[1])), indent=2))
