"""Detect the listicle-abstract pattern: 'rests on N premises', 'consists of N components',
mechanical thesis enumerations where N consecutive numbered/bulleted items begin with
the same anaphoric word.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .lint_common import load_markdown, load_rules

LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", re.MULTILINE)


def _phrase_findings(text: str, patterns: list[str]) -> list[dict]:
    out: list[dict] = []
    for pat in patterns:
        for match in re.finditer(pat, text, flags=re.IGNORECASE):
            line_no = text[: match.start()].count("\n") + 1
            out.append({
                "rule": "listicle-abstract",
                "pattern": pat,
                "snippet": match.group(0),
                "line": line_no,
            })
    return out


def _anaphora_findings(text: str, min_repeats: int, window_lines: int) -> list[dict]:
    out: list[dict] = []
    items: list[tuple[int, str, str]] = []
    for match in LIST_ITEM.finditer(text):
        line_no = text[: match.start()].count("\n") + 1
        body = match.group(3).strip()
        first_word = body.split()[0] if body else ""
        items.append((line_no, first_word, body))

    i = 0
    while i < len(items):
        run_first = items[i][1]
        run_start = items[i][0]
        j = i + 1
        while j < len(items) and items[j][1] == run_first and items[j][0] - items[j - 1][0] <= window_lines:
            j += 1
        run_len = j - i
        if run_len >= min_repeats and run_first:
            out.append({
                "rule": "listicle-anaphora",
                "first_word": run_first,
                "run_length": run_len,
                "line": run_start,
                "snippet": "\n".join(b for _, _, b in items[i:j])[:400],
            })
            i = j
        else:
            i += 1
    return out


def lint_listicle_abstract(path: Path) -> list[dict]:
    text = load_markdown(path)
    rules = load_rules()
    patterns = rules.get("listicle_patterns", [])
    min_repeats = int(rules.get("listicle_anaphora_min_repeats", 3))
    window = int(rules.get("listicle_anaphora_window_lines", 6))

    findings = _phrase_findings(text, patterns)
    findings += _anaphora_findings(text, min_repeats, window)
    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: lint_listicle_abstract.py <markdown-file>", file=sys.stderr)
        return 2
    findings = lint_listicle_abstract(Path(argv[1]))
    print(json.dumps(findings, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
