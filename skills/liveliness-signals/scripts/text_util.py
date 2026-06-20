"""Lightweight sentence view for the liveliness scorers.

Reuses profile_metrics._nlp() (POS tagger on; lemmatizer/ner off), so content
words are lowercased alpha non-stop token TEXT, not lemmas.
"""
from __future__ import annotations
from dataclasses import dataclass

from scripts.profile_metrics import _nlp


@dataclass(frozen=True)
class Sentence:
    text: str
    first: str            # first lowercased alpha token ("" if none)
    content: frozenset    # lowercased alpha non-stop token texts
    n_alpha: int


def iter_sentences(text: str) -> list[Sentence]:
    nlp = _nlp()
    out: list[Sentence] = []
    for sent in nlp(text).sents:
        alpha = [t for t in sent if t.is_alpha]
        if not alpha:
            continue
        first = alpha[0].text.lower()
        content = frozenset(t.text.lower() for t in alpha if not t.is_stop)
        out.append(Sentence(text=sent.text.strip(), first=first,
                            content=content, n_alpha=len(alpha)))
    return out


def iter_spacy_sentences(text: str) -> list:
    """Yield spaCy sentence spans (parser + tagger on) for dependency scorers."""
    nlp = _nlp()
    return [s for s in nlp(text).sents if any(t.is_alpha for t in s)]
