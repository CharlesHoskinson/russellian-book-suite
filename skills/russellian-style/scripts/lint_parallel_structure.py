"""Detect bullet/numbered lists whose items start with mismatched grammatical types."""
from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from pathlib import Path

import spacy

from .lint_common import load_markdown

LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+\.)\s+(.*)$")


@lru_cache(maxsize=1)
def _nlp():
    return spacy.load("en_core_web_sm")


def _classify_opening(item_text: str) -> str:
    nlp = _nlp()
    stripped = item_text.strip()
    if not stripped:
        return "unknown"
    doc = nlp(stripped)
    if not doc:
        return "unknown"
    first = doc[0]
    # Pronoun subjects are detected reliably without any reparse trick.
    if first.lower_ in ("you", "we", "i", "they", "users"):
        return "pronoun_subject"
    # spaCy's PoS tagger frequently mislabels sentence-initial imperative verbs
    # as nouns when the verb is a common verb/noun homograph (e.g. "Load",
    # "Start", "Run"). Reparsing with a "Please <lower>..." prefix forces the
    # tagger into an imperative reading without changing the tag for items that
    # really are noun phrases ("Configuration of the environment" stays NN).
    probe_text = "Please " + stripped[0].lower() + stripped[1:]
    probe = nlp(probe_text)
    probe_first = probe[1] if len(probe) > 1 else first
    if probe_first.tag_ in ("VB", "VBP") or (
        probe_first.pos_ == "VERB" and probe_first.tag_ in ("VB", "VBP")
    ):
        return "imperative_verb"
    if probe_first.tag_ == "VBG" or first.tag_ == "VBG":
        return "gerund"
    if first.pos_ in ("NOUN", "PROPN"):
        return "noun_phrase"
    if first.pos_ == "ADJ":
        return "adjective"
    return first.pos_.lower()


def _collect_lists(text: str) -> list[list[tuple[int, str]]]:
    lists: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    current_indent: str | None = None
    for line_idx, raw in enumerate(text.splitlines(), start=1):
        match = LIST_ITEM.match(raw)
        if match:
            indent = match.group(1)
            content = match.group(3).strip()
            if current_indent is None or indent == current_indent:
                current_indent = indent
                current.append((line_idx, content))
            else:
                if current:
                    lists.append(current)
                current = [(line_idx, content)]
                current_indent = indent
        else:
            if raw.strip() == "" and current:
                continue
            if current:
                lists.append(current)
                current = []
                current_indent = None
    if current:
        lists.append(current)
    return lists


def lint_parallel_structure(path: Path) -> list[dict]:
    text = load_markdown(path)
    findings: list[dict] = []
    for items in _collect_lists(text):
        if len(items) < 2:
            continue
        classifications = [(line, body, _classify_opening(body)) for line, body in items]
        kinds = {c for _, _, c in classifications}
        if len(kinds) > 1:
            findings.append({
                "rule": "parallel-structure",
                "start_line": classifications[0][0],
                "end_line": classifications[-1][0],
                "items": [
                    {"line": line, "item": body, "kind": kind}
                    for line, body, kind in classifications
                ],
            })
    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: lint_parallel_structure.py <markdown-file>", file=sys.stderr)
        return 2
    findings = lint_parallel_structure(Path(argv[1]))
    print(json.dumps(findings, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
