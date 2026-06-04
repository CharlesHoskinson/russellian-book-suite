"""Flag passages lacking analogy or saturated with abstract nouns."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .lint_common import load_markdown, _split_paragraphs, _is_code_block, _is_heading, _is_list_marker

_ANALOGY = re.compile(
    r"\b(like|as if|as though|imagine|picture|think of|similar to|"
    r"the way|just as|kind of like|sort of like|as when|"
    # predicate metaphor and explicit comparison, which carry an analogy without a
    # simile keyword ("noise wearing a tie", "better than a coin flip", "a force in disguise")
    r"wearing|wears|dressed up|in disguise|no better than|better than a|worse than a)\b",
    re.IGNORECASE,
)
_ABSTRACT_SUFFIX = re.compile(
    r"\b\w+(?:tion|sion|ment|ness|ity|ance|ence|ism|ization|isation)\b",
    re.IGNORECASE,
)
DEFAULT_ABSTRACT_RATIO = 0.18  # abstract nouns / total words
_ANALOGY_MIN_WORDS = 30   # min paragraph length to require an analogy marker
_ABSTRACT_MIN_WORDS = 10  # min paragraph length to check abstract-noun density


def lint_concreteness(path: Path, max_abstract_ratio: float = DEFAULT_ABSTRACT_RATIO) -> list[dict]:
    text = load_markdown(path)
    findings: list[dict] = []
    for start_line, para in _split_paragraphs(text):
        if _is_code_block(para) or _is_heading(para) or _is_list_marker(para):
            continue
        words = para.split()
        if len(words) < _ABSTRACT_MIN_WORDS:
            continue
        flat = " ".join(words)
        snippet = flat[:160]
        if len(words) >= _ANALOGY_MIN_WORDS and not _ANALOGY.search(flat):
            findings.append({
                "rule": "analogy-absent",
                "sentence": snippet,
                "line": start_line,
                "col": 1,
            })
        abstract = len(_ABSTRACT_SUFFIX.findall(flat))
        if abstract / len(words) > max_abstract_ratio:
            findings.append({
                "rule": "abstraction-heavy",
                "ratio": round(abstract / len(words), 3),
                "sentence": snippet,
                "line": start_line,
                "col": 1,
            })
    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: lint_concreteness.py <markdown-file>", file=sys.stderr)
        return 2
    findings = lint_concreteness(Path(argv[1]))
    print(json.dumps(findings, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
