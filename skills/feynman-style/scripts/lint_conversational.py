"""Reward conversational warmth; flag paragraphs that read cold/formal."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .lint_common import load_markdown, _split_paragraphs, _is_code_block, _is_heading, _is_list_marker

_CONTRACTION = re.compile(r"\b\w+'(?:s|re|ve|ll|d|t|m)\b", re.IGNORECASE)
_SECOND_PERSON = re.compile(r"\b(your|you|we|let's)\b", re.IGNORECASE)
_DIRECT_OPENER = re.compile(r"\b(now|well|so|here's the thing|imagine|suppose|think about)\b", re.IGNORECASE)
DEFAULT_MIN = 1


def _markers(paragraph: str) -> int:
    n = len(_CONTRACTION.findall(paragraph))
    n += len(_SECOND_PERSON.findall(paragraph))
    n += len(_DIRECT_OPENER.findall(paragraph))
    n += paragraph.count("?")
    return n


def lint_conversational(path: Path, min_per_paragraph: int = DEFAULT_MIN) -> list[dict]:
    text = load_markdown(path)
    findings: list[dict] = []
    for start_line, para in _split_paragraphs(text):
        if _is_code_block(para) or _is_heading(para) or _is_list_marker(para):
            continue
        if len(para.split()) < 25:
            continue  # only judge substantial paragraphs
        if _markers(para) < min_per_paragraph:
            findings.append({
                "rule": "conversational-cold",
                "sentence": " ".join(para.split())[:160],
                "line": start_line,
                "col": 1,
            })
    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: lint_conversational.py <markdown-file>", file=sys.stderr)
        return 2
    findings = lint_conversational(Path(argv[1]))
    print(json.dumps(findings, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
