"""Detect hedging vocabulary in markdown prose."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .lint_common import iter_sentences, load_markdown, load_rules


AMBIGUOUS_TITLE_CASE = {"may", "might", "could", "should", "would", "tends"}


def lint_hedges(path: Path) -> list[dict]:
    text = load_markdown(path)
    rules = load_rules()
    terms = sorted(rules["hedge_terms"], key=len, reverse=True)
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(t) for t in terms) + r")\b",
        flags=re.IGNORECASE,
    )

    findings: list[dict] = []
    for sentence in iter_sentences(text):
        for match in pattern.finditer(sentence.text):
            matched_token = match.group(1)
            lower = matched_token.lower()
            if lower in AMBIGUOUS_TITLE_CASE and matched_token[0].isupper():
                continue  # likely a proper noun or sentence-initial month name
            findings.append({
                "rule": "no-hedging",
                "term": lower,
                "sentence": sentence.text,
                "line": sentence.line,
                "col": sentence.col + match.start(),
            })
    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: lint_hedges.py <markdown-file>", file=sys.stderr)
        return 2
    findings = lint_hedges(Path(argv[1]))
    print(json.dumps(findings, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
