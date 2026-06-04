"""Flag Latinate jargon that has a plain Anglo-Saxon substitute."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .lint_common import iter_sentences, load_markdown

# Built-in default; Task 12 lets feynman-rules.json override via "latinate_substitutions".
_DEFAULT_MAP = {
    "utilize": "use", "utilizes": "uses", "utilized": "used",
    "facilitate": "help", "demonstrate": "show", "demonstration": "demo",
    "endeavor": "try", "commence": "start", "terminate": "end",
    "subsequent": "later", "prior to": "before", "in order to": "to",
    "approximately": "about", "sufficient": "enough", "additional": "more",
    "methodology": "method", "functionality": "feature", "leverage": "use",
    "ascertain": "find out", "necessitate": "need", "fundamental": "basic",
}


def _load_map() -> dict:
    rules = Path(__file__).resolve().parent.parent / "assets" / "feynman-rules.json"
    if rules.exists():
        data = json.loads(rules.read_text(encoding="utf-8"))
        return data.get("latinate_substitutions", _DEFAULT_MAP)
    return _DEFAULT_MAP


def lint_latinate_diction(path: Path) -> list[dict]:
    text = load_markdown(path)
    mapping = _load_map()
    terms = sorted(mapping, key=len, reverse=True)
    pattern = re.compile(r"\b(" + "|".join(re.escape(t) for t in terms) + r")\b", re.IGNORECASE)
    findings: list[dict] = []
    for sentence in iter_sentences(text):
        for m in pattern.finditer(sentence.text):
            term = m.group(1).lower()
            line, col = _match_line_col(sentence.line, sentence.col, sentence.text, m.start())
            findings.append({
                "rule": "latinate-diction",
                "term": term,
                "suggestion": mapping[term],
                "sentence": sentence.text,
                "line": line,
                "col": col,
            })
    return findings


def _match_line_col(sent_line: int, sent_col: int, sent_text: str, offset: int) -> tuple[int, int]:
    """Resolve the 1-indexed line/col of a match within a (possibly multi-line)
    sentence. Adding the intra-sentence offset to the sentence's start column is
    only correct on the sentence's first physical line; when the match sits on a
    continuation line the line must be bumped and the column reset relative to
    the last newline."""
    prefix = sent_text[:offset]
    newlines = prefix.count("\n")
    if newlines == 0:
        return sent_line, sent_col + offset
    return sent_line + newlines, offset - prefix.rfind("\n")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: lint_latinate_diction.py <markdown-file>", file=sys.stderr)
        return 2
    findings = lint_latinate_diction(Path(argv[1]))
    print(json.dumps(findings, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
