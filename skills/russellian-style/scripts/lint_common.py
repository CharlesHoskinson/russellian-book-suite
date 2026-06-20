"""Shared utilities for the russellian-style linters."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterator

import spacy

ASSETS = Path(__file__).resolve().parent.parent / "assets"


@dataclass(frozen=True)
class Sentence:
    text: str
    line: int           # 1-indexed line where the sentence starts
    col: int            # 1-indexed column
    paragraph_idx: int  # 0-indexed paragraph


def load_markdown(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def load_rules(name: str = "russellian-rules.json") -> dict:
    return json.loads((ASSETS / name).read_text(encoding="utf-8"))


def iter_sentences(text: str) -> Iterator[Sentence]:
    """Yield sentences with 1-indexed line/col positions.

    Skips paragraphs that are headings, fenced code blocks, indented
    code blocks (4-space prefix), or list-marker lines.

    Sentence segmentation uses the spaCy sentencizer, which avoids
    fragmenting on abbreviations, decimals, and initials.
    """
    paragraphs = _split_paragraphs(text)
    for para_idx, (para_line, para_text) in enumerate(paragraphs):
        if _is_code_block(para_text) or _is_heading(para_text) or _is_list_marker(para_text):
            continue
        offsets = _sentence_offsets(para_text)
        for raw_text, char_offset in offsets:
            stripped = raw_text.strip()
            if not stripped:
                continue
            line, col = _resolve_line_col(para_line, para_text, char_offset)
            yield Sentence(text=stripped, line=line, col=col, paragraph_idx=para_idx)


def _split_paragraphs(text: str) -> list[tuple[int, str]]:
    """Return (starting_line_1indexed, paragraph_text) pairs."""
    out: list[tuple[int, str]] = []
    lines = text.splitlines()
    current: list[str] = []
    current_start = 1
    for idx, raw in enumerate(lines, start=1):
        if raw.strip() == "":
            if current:
                out.append((current_start, "\n".join(current)))
                current = []
            current_start = idx + 1
        else:
            if not current:
                current_start = idx
            current.append(raw)
    if current:
        out.append((current_start, "\n".join(current)))
    return out


def _is_code_block(para: str) -> bool:
    return para.lstrip().startswith("```") or para.startswith("    ")


def _is_heading(para: str) -> bool:
    return para.lstrip().startswith("#")


def _is_list_marker(para: str) -> bool:
    return bool(re.match(r"^\s*([-*+]|\d+\.)\s", para))


@lru_cache(maxsize=1)
def _nlp_sentencizer():
    nlp = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])
    if "sentencizer" not in nlp.pipe_names and "senter" not in nlp.pipe_names:
        nlp.add_pipe("sentencizer")
    return nlp


def _sentence_offsets(para_text: str) -> list[tuple[str, int]]:
    nlp = _nlp_sentencizer()
    doc = nlp(para_text)
    return [(sent.text, sent.start_char) for sent in doc.sents]


def _resolve_line_col(para_start_line: int, para_text: str, char_offset: int) -> tuple[int, int]:
    prefix = para_text[:char_offset]
    line_offset = prefix.count("\n")
    if line_offset:
        col = char_offset - prefix.rfind("\n")
    else:
        col = char_offset + 1
    return para_start_line + line_offset, col
