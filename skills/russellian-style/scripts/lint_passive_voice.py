"""Detect passive-voice constructions using spaCy dependency parsing."""
from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

import spacy

from .lint_common import iter_sentences, load_markdown


@lru_cache(maxsize=1)
def _nlp():
    return spacy.load("en_core_web_sm")


def _has_passive_dep(spacy_doc) -> bool:
    return any(tok.dep_ in ("nsubjpass", "auxpass", "csubjpass") for tok in spacy_doc)


def lint_passive_voice(path: Path) -> list[dict]:
    text = load_markdown(path)
    nlp = _nlp()
    findings: list[dict] = []
    for sentence in iter_sentences(text):
        doc = nlp(sentence.text)
        if _has_passive_dep(doc):
            findings.append({
                "rule": "active-voice",
                "sentence": sentence.text,
                "line": sentence.line,
                "col": sentence.col,
            })
    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: lint_passive_voice.py <markdown-file>", file=sys.stderr)
        return 2
    findings = lint_passive_voice(Path(argv[1]))
    print(json.dumps(findings, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
