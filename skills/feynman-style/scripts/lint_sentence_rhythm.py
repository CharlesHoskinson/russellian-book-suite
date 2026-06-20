"""Detect rhythm uniformity: runs of N consecutive sentences with identical
word counts (within tolerance) or identical sentence openings.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .lint_common import iter_sentences, load_markdown

# Constants inlined to decouple from feynman-rules.json.
RHYTHM_RUN_MIN: int = 4
RHYTHM_TOLERANCE: int = 3


def _word_count(s: str) -> int:
    return len(re.findall(r"\b\w+\b", s))


def _first_word(s: str) -> str:
    match = re.match(r"\W*(\w+)", s)
    return match.group(1).lower() if match else ""


def lint_sentence_rhythm(path: Path) -> list[dict]:
    text = load_markdown(path)
    min_run = RHYTHM_RUN_MIN
    tolerance = RHYTHM_TOLERANCE

    sentences = list(iter_sentences(text))
    findings: list[dict] = []
    if len(sentences) < min_run:
        return findings

    counts = [_word_count(s.text) for s in sentences]
    firsts = [_first_word(s.text) for s in sentences]

    # Uniform word count run
    i = 0
    while i <= len(counts) - min_run:
        window = counts[i : i + min_run]
        if max(window) - min(window) <= tolerance:
            findings.append({
                "rule": "rhythm-uniform-length",
                "line": sentences[i].line,
                "start_line": sentences[i].line,
                "run_length": min_run,
                "word_counts": window,
                "snippet": " ".join(s.text for s in sentences[i : i + min_run])[:400],
            })
            i += min_run
        else:
            i += 1

    # Repeated opening run
    i = 0
    while i < len(firsts):
        run_first = firsts[i]
        if not run_first:
            i += 1
            continue
        j = i + 1
        while j < len(firsts) and firsts[j] == run_first:
            j += 1
        run_len = j - i
        if run_len >= min_run:
            findings.append({
                "rule": "rhythm-repeated-opening",
                "first_word": run_first,
                "line": sentences[i].line,
                "start_line": sentences[i].line,
                "run_length": run_len,
                "snippet": " ".join(s.text for s in sentences[i:j])[:400],
            })
            i = j
        else:
            i += 1

    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: lint_sentence_rhythm.py <markdown-file>", file=sys.stderr)
        return 2
    findings = lint_sentence_rhythm(Path(argv[1]))
    print(json.dumps(findings, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
