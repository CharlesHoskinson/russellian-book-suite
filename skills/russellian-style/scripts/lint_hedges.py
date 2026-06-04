"""Detect hedging vocabulary in markdown prose."""
from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from pathlib import Path

from .lint_common import iter_sentences, load_markdown, load_rules


# Modals that also occur as proper nouns (e.g. "May" the month/surname). A
# capitalized occurrence is skipped only when the part-of-speech tagger
# classifies it as a proper noun (or it falls inside a date/person entity),
# not merely because it is capitalized — that blanket rule dropped genuine
# mid-sentence hedges. The whitelist omits "tends": the rules file has only the
# multi-word "tends to"/"tend to", so a bare "tends" can never match group(1)
# and the entry was dead config.
AMBIGUOUS_TITLE_CASE = {"may", "might", "could", "should", "would"}


@lru_cache(maxsize=1)
def _nlp_tagger():
    import spacy
    return spacy.load("en_core_web_sm", disable=["lemmatizer"])


def _is_proper_noun(sentence_text: str, token_start: int, token_text: str) -> bool:
    """True if the token at token_start parses as a proper noun / name / date."""
    doc = _nlp_tagger()(sentence_text)
    for tok in doc:
        if tok.idx == token_start and tok.text == token_text:
            return tok.pos_ == "PROPN" or tok.ent_type_ in ("DATE", "PERSON", "GPE")
    # Fall back to a containment check if offsets do not line up exactly.
    for tok in doc:
        if tok.text == token_text and tok.idx <= token_start < tok.idx + len(tok.text):
            return tok.pos_ == "PROPN" or tok.ent_type_ in ("DATE", "PERSON", "GPE")
    return False


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
            if (
                lower in AMBIGUOUS_TITLE_CASE
                and matched_token[0].isupper()
                and _is_proper_noun(sentence.text, match.start(), matched_token)
            ):
                continue  # capitalized modal parsed as a proper noun (month/surname)
            if lower == "rather" and "than" in sentence.text[match.end():].lower():
                continue  # "rather ... than" is contrastive/preference, not a hedge
            line, col = _match_line_col(sentence.line, sentence.col, sentence.text, match.start())
            findings.append({
                "rule": "no-hedging",
                "term": lower,
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
        print("usage: lint_hedges.py <markdown-file>", file=sys.stderr)
        return 2
    findings = lint_hedges(Path(argv[1]))
    print(json.dumps(findings, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
