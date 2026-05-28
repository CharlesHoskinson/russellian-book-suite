"""Humanity-token closer linter: flags paragraph closers shaped like aphorisms.

Pure stdlib + re. Cross-imports the public ``strip_quotes`` helper from
``lint_ornament`` (REQ-VOICE-026). Imports nothing from ``lint_common`` (which
loads spaCy at module top) so this module runs under the CI ``[ci]`` extra
without the spaCy English model.

The instrument is named honestly. It measures the density of paragraph-final
sentences that fit the chassis closer shape (8-18-word verdict was the original
spec; the rebuilt range is 6-28 to cover Russell's characteristic 20-30-word
sweeping closers without losing the 8-word "Slowness, well defended, is a kind
of strength" case). Five gates per closer:

  1. Word count in [6, 28].
  2. Contains a humanity-generalising token from the closed list (see ``_HUMANITY``).
  3. Contains no concrete-instance marker (capitalised non-initial word,
     4-digit year, or numeric quantity).
  4. Contains no first-person-singular token (``\\bI\\b`` or ``\\bmy\\b``).
  5. (Implicit: quoted spans are excluded by ``strip_quotes`` before scanning.)

One finding per qualifying closer. Severity advisory; tier advisory; the linter
does not gate. ``voice_eval._signals`` converts ``len(fn(path))`` to per-1000
density. The descriptive threshold for "performs wisdom on a metronome" (the
critique that motivated the linter) is ~6 closers per 1000 words.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.lint_ornament import strip_quotes


_HUMANITY = (
    "we", "our", "us", "ourselves",
    "mankind", "humanity", "civilisation", "civilization",
    "modern life", "the modern world",
    "most people", "most of us", "the rest of us", "none of us", "each of us",
    "men", "man",
    "nature",
    "no one", "anyone", "everyone",
)
_HUMANITY_RE = re.compile(
    r"(?:^|[\s,;:()\-])(" + "|".join(re.escape(t) for t in _HUMANITY) + r")(?=[\s,.;:!?()\-]|$)",
    re.IGNORECASE,
)

_FIRST_PERSON_SINGULAR = re.compile(r"\b(I|my)\b")
_YEAR = re.compile(r"\b\d{4}\b")
_NUMERIC = re.compile(r"\b\d+\b")
# Proper-noun proxy: capitalised non-initial word. Skip the first word of the
# closer because sentence-initial capitalisation is not a proper-noun signal.
_CAPITALISED_NON_INITIAL = re.compile(r"(?<=\s)[A-Z][a-z]+")

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in _PARAGRAPH_SPLIT.split(text) if p.strip()]


def _closing_sentence(paragraph: str) -> str:
    """Return the final non-empty sentence of the paragraph, or '' if none."""
    sents = [s.strip() for s in _SENTENCE_SPLIT.split(paragraph.strip()) if s.strip()]
    return sents[-1] if sents else ""


def _is_humanity_token_closer(sentence: str) -> bool:
    if not sentence:
        return False
    words = sentence.split()
    n = len(words)
    if n < 6 or n > 28:
        return False
    if not _HUMANITY_RE.search(sentence):
        return False
    if _FIRST_PERSON_SINGULAR.search(sentence):
        return False
    if _YEAR.search(sentence):
        return False
    if _NUMERIC.search(sentence):
        return False
    if _CAPITALISED_NON_INITIAL.search(sentence):
        return False
    return True


def lint_humanity_token_closers(path: Path) -> list[dict]:
    text = strip_quotes(Path(path).read_text(encoding="utf-8"))
    findings: list[dict] = []
    for i, para in enumerate(_paragraphs(text)):
        closer = _closing_sentence(para)
        if _is_humanity_token_closer(closer):
            findings.append({
                "rule": "humanity-token-closer",
                "paragraph_index": i,
                "closer": closer,
                "tier": "advisory",
                "severity": "advisory",
            })
    return findings


if __name__ == "__main__":
    import sys
    print(json.dumps(lint_humanity_token_closers(Path(sys.argv[1])), indent=2))
