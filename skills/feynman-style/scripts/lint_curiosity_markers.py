"""Reward honest-doubt / puzzle framing; flag long passages with none."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .lint_common import load_markdown, _split_paragraphs, _is_code_block, _is_heading, _is_list_marker

# These read as hedges to Russell but are Feynman curiosity moves. See the
# Surface/Integrity partition in assets/feynman-rules.json and references/negative-triggers.md.
_CURIOSITY = re.compile(
    r"(nobody (?:really )?knows|the funny thing is|here'?s the puzzle|"
    r"it turns out|what'?s (?:really )?going on|the strange thing|"
    r"you might (?:ask|wonder)|the question is|why (?:on earth|in the world)|"
    r"the mystery|nobody had figured|"
    r"maybe|perhaps|what if|how do you|could a|could it)",
    re.IGNORECASE,
)


def count_markers(text: str) -> int:
    # A rhetorical question is the core Feynman curiosity move; count question
    # marks alongside the honest-doubt phrase list so warmed prose is not flagged
    # as curiosity-absent merely because its puzzle-framing uses "?" rather than a
    # whitelisted phrase.
    return len(_CURIOSITY.findall(text)) + text.count("?")


def lint_curiosity_markers(path: Path, min_per_long_passage: int = 1, long_words: int = 30) -> list[dict]:
    text = load_markdown(path)
    findings: list[dict] = []
    for start_line, para in _split_paragraphs(text):
        if _is_code_block(para) or _is_heading(para) or _is_list_marker(para):
            continue
        words = para.split()
        if len(words) < long_words:
            continue
        if count_markers(" ".join(words)) < min_per_long_passage:
            findings.append({
                "rule": "curiosity-absent",
                "sentence": " ".join(words)[:160],
                "line": start_line,
                "col": 1,
            })
    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: lint_curiosity_markers.py <markdown-file>", file=sys.stderr)
        return 2
    findings = lint_curiosity_markers(Path(argv[1]))
    print(json.dumps(findings, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
