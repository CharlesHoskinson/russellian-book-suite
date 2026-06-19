"""Deterministic, stats-only metrics over corpus text. spaCy for sentence split."""
from __future__ import annotations
from collections import Counter
from functools import lru_cache
from statistics import mean, pstdev
import spacy


@lru_cache(maxsize=1)
def _nlp():
    nlp = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])
    if "sentencizer" not in nlp.pipe_names and "senter" not in nlp.pipe_names:
        nlp.add_pipe("sentencizer")
    return nlp


def sentence_lengths(texts: list[str]) -> list[int]:
    nlp = _nlp()
    out: list[int] = []
    for text in texts:
        for sent in nlp(text).sents:
            n = sum(1 for t in sent if not t.is_space and not t.is_punct)
            if n > 0:
                out.append(n)
    return out


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = min(len(sorted_vals) - 1, int(round(p * (len(sorted_vals) - 1))))
    return round(float(sorted_vals[k]), 6)


def cadence_corridor(lengths: list[int]) -> dict:
    if not lengths:
        return {"p10": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0, "p90": 0.0, "cv": 0.0, "count": 0}
    s = sorted(lengths)
    mu = mean(s)
    cv = round(pstdev(s) / mu, 6) if mu else 0.0
    return {
        "p10": _percentile(s, 0.10), "p25": _percentile(s, 0.25),
        "p50": _percentile(s, 0.50), "p75": _percentile(s, 0.75),
        "p90": _percentile(s, 0.90), "cv": cv, "count": len(s),
    }


_DISCOURSE_MARKERS = {"but", "so", "now", "then", "because", "however", "instead",
                      "therefore", "and", "yet", "still", "here"}
_DIRECT_ADDRESS = {"you", "your", "you're", "let's", "we", "our"}
_EXAMPLE_MARKERS = ("for example", "for instance", "imagine", "picture", "think about",
                    "consider", "watch", "say")


def _sentences(texts: list[str]):
    nlp = _nlp()
    for text in texts:
        for sent in nlp(text).sents:
            toks = [t for t in sent if not t.is_space]
            if toks:
                yield sent.text.strip(), toks


def diction_device_metrics(texts: list[str]) -> dict:
    first_words: Counter = Counter()
    n_sent = 0
    n_marker = 0
    n_address = 0
    short = 0
    long = 0
    example_positions: list[int] = []
    for i, (sent_text, toks) in enumerate(_sentences(texts)):
        n_sent += 1
        words = [t.text.lower() for t in toks if not t.is_punct]
        if words:
            first_words[words[0]] += 1
            if words[0] in _DISCOURSE_MARKERS:
                n_marker += 1
            if any(w in _DIRECT_ADDRESS for w in words):
                n_address += 1
            wl = len(words)
            if wl <= 6:
                short += 1
            elif wl >= 20:
                long += 1
        low = sent_text.lower()
        if any(m in low for m in _EXAMPLE_MARKERS):
            example_positions.append(i)
    total_first = sum(first_words.values()) or 1
    top = {w: round(c / total_first, 6) for w, c in first_words.most_common(10)}
    gaps = [b - a for a, b in zip(example_positions, example_positions[1:])]
    return {
        "first_word_dist": top,
        "discourse_marker_rate": round(n_marker / n_sent, 6) if n_sent else 0.0,
        "direct_address_rate": round(n_address / n_sent, 6) if n_sent else 0.0,
        "short_long_ratio": round(short / long, 6) if long else float(short),
        "example_spacing": round(sum(gaps) / len(gaps), 6) if gaps else 0.0,
    }


def modifier_ratios(texts: list[str], min_alpha: int = 8) -> list[float]:
    """Per-sentence modifier (ADJ+ADV) ratio over alpha tokens.

    Only sentences with at least `min_alpha` alpha tokens are measured, matching
    the russellian-style signal-density linter's assessment threshold. The shared
    `_nlp()` keeps the POS tagger (only ner/lemmatizer are disabled), so `pos_`
    is available.
    """
    nlp = _nlp()
    out: list[float] = []
    for text in texts:
        for sent in nlp(text).sents:
            content = [t for t in sent if t.is_alpha]
            if len(content) < min_alpha:
                continue
            mods = sum(1 for t in content if t.pos_ in ("ADJ", "ADV"))
            out.append(mods / len(content))
    return out
